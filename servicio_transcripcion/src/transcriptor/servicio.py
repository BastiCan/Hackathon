"""Lógica del transcriptor: Amazon Transcribe por lotes, más un modo mock sin AWS.

No hay base de datos. El trabajo vive en Transcribe y el JSON final en
s3://BUCKET/resultados/{id_trabajo}.json. El nombre del trabajo (prefijo + id_captura)
es la clave de idempotencia: Transcribe no acepta dos trabajos con el mismo nombre.

Al terminar, el audio y el texto se entregan a ProcesarNota en BUCKET_CAPTURAS:
capturas/{id_captura}/original/audio.<ext> y capturas/{id_captura}/texto.json.
El meta.json de la captura lo escribe otra parte del sistema.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from importlib import resources
from typing import Any

from botocore.exceptions import ClientError

from .audio import FormatoAudio
from .config import IDIOMAS, Config, cargar_config
from .contrato import ErrorResultado, Palabra, ResultadoTranscripcion
from .conversion import convertir_salida

logger = logging.getLogger("transcriptor")

PROVEEDOR = "amazon_transcribe"
MODELO = "batch-standard"
TERMINALES = ("COMPLETED", "FAILED")
# ProcesarNota solo acepta capturas/CAP-<ULID>/ (ver core/capturas.py de integra-procesador).
ID_CAPTURA_PROCESADOR = re.compile(r"^CAP-[0-9A-HJKMNP-TV-Z]{26}$")


class IdEnUso(Exception):
    """Ya existe un trabajo con ese nombre en la cuenta, pero su audio no está en este bucket."""


class MetaPendiente(Exception):
    """La captura aún no tiene meta.json. ProcesarNota marca ERROR si recibe texto.json antes."""

    def __init__(self, resultado: ResultadoTranscripcion) -> None:
        super().__init__(f"Falta meta.json de {resultado.id_captura}")
        self.resultado = resultado


def iso_utc(momento: datetime | None = None) -> str:
    momento = momento or datetime.now(timezone.utc)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _codigo(exc: ClientError) -> str:
    return exc.response.get("Error", {}).get("Code", "")


def _no_existe_objeto(exc: ClientError) -> bool:
    return _codigo(exc) in ("NoSuchKey", "404", "NotFound")


def _no_existe_trabajo(exc: ClientError) -> bool:
    # Para un trabajo inexistente, Transcribe responde BadRequestException ("couldn't be found").
    mensaje = exc.response.get("Error", {}).get("Message", "").lower()
    return _codigo(exc) == "NotFoundException" or (_codigo(exc) == "BadRequestException" and "found" in mensaje)


class ServicioTranscribe:
    def __init__(self, config: Config, s3: Any, transcribe: Any) -> None:
        self.config = config
        self.s3 = s3
        self.transcribe = transcribe

    def iniciar(
        self, id_captura: str, audio: bytes, formato: FormatoAudio, idioma: str | None = None
    ) -> ResultadoTranscripcion:
        """Sube el audio e inicia el trabajo. Si ese id_captura ya se envió, devuelve el trabajo existente."""
        id_trabajo = self.config.prefijo_trabajo + id_captura
        existente = self._obtener_trabajo(id_trabajo)
        if existente is not None:
            logger.info("trabajo_existente", extra={"id_trabajo": id_trabajo})
            return self._resultado_existente(existente)
        clave_audio = f"audio/{id_trabajo}.{formato.extension}"
        self.s3.put_object(Bucket=self.config.bucket, Key=clave_audio, Body=audio, ContentType=formato.tipo_mime)
        try:
            # Sin MediaFormat: Transcribe detecta el formato y se evitan rechazos mp4/m4a.
            respuesta = self.transcribe.start_transcription_job(
                TranscriptionJobName=id_trabajo,
                LanguageCode=idioma or self.config.idioma,
                Media={"MediaFileUri": f"s3://{self.config.bucket}/{clave_audio}"},
                OutputBucketName=self.config.bucket,
                OutputKey=f"transcripciones/{id_trabajo}.json",
            )
        except ClientError as exc:
            if _codigo(exc) != "ConflictException":
                raise
            existente = self._obtener_trabajo(id_trabajo)  # otra solicitud igual llegó primero
            if existente is None:
                raise
            return self._resultado_existente(existente)
        logger.info(
            "trabajo_iniciado",
            extra={"id_trabajo": id_trabajo, "bytes_audio": len(audio), "formato": formato.extension},
        )
        return self._armar(respuesta["TranscriptionJob"], "transcribiendo")

    def consultar(self, id_trabajo: str, exigir_entrega: bool = False) -> ResultadoTranscripcion | None:
        """JSON actual del trabajo, o None si no existe o no es de este servicio.

        Si Transcribe ya terminó y el resultado aún no estaba guardado, lo guarda (por si se perdió el evento).
        Si falta el meta.json de la captura, devuelve el resultado sin guardarlo, para reintentar la entrega
        en la próxima consulta. Con exigir_entrega=True, en ese caso lanza MetaPendiente.
        """
        if not id_trabajo.startswith(self.config.prefijo_trabajo):
            return None
        guardado = self._leer_resultado(id_trabajo)
        if guardado is not None:
            return guardado
        trabajo = self._obtener_trabajo(id_trabajo)
        if trabajo is None or not self._es_propio(trabajo):
            return None
        try:
            return self._estado_actual(trabajo)
        except MetaPendiente as exc:
            if exigir_entrega:
                raise
            return exc.resultado

    def finalizar(self, trabajo: dict[str, Any]) -> ResultadoTranscripcion:
        """Arma el JSON final, entrega el texto a ProcesarNota, guarda el JSON y borra el audio.

        Repetirlo da el mismo resultado. Si la entrega falla, no se guarda nada y se puede reintentar.
        """
        id_trabajo = trabajo["TranscriptionJobName"]
        if trabajo["TranscriptionJobStatus"] == "FAILED":
            motivo = trabajo.get("FailureReason") or "Amazon Transcribe no informó el motivo"
            resultado = self._fallido(trabajo, "transcripcion_fallida", motivo)
        else:
            resultado = self._completado(trabajo)
        self._entregar_texto(resultado, trabajo)
        self.s3.put_object(
            Bucket=self.config.bucket,
            Key=f"resultados/{id_trabajo}.json",
            Body=resultado.model_dump_json().encode("utf-8"),
            ContentType="application/json; charset=utf-8",
        )
        self._borrar_audio(trabajo)
        logger.info(
            "trabajo_finalizado",
            extra={"id_trabajo": id_trabajo, "estado": resultado.estado, "palabras": len(resultado.palabras)},
        )
        return resultado

    def _entregar_texto(self, resultado: ResultadoTranscripcion, trabajo: dict[str, Any]) -> None:
        """Deja el audio y texto.json de la captura en el bucket de ProcesarNota.

        El audio se copia a capturas/{id}/original/audio.<ext> y texto.json lo nombra en
        partes[0].archivo, así ProcesarNota guarda esa ruta en archivo_s3 de la observación.
        texto.json se escribe una sola vez.
        """
        destino = self.config.bucket_capturas
        if not destino or resultado.estado != "completado" or not resultado.texto_completo:
            return
        if not ID_CAPTURA_PROCESADOR.match(resultado.id_captura):
            logger.info("entrega_omitida", extra={"id_trabajo": resultado.id_trabajo, "motivo": "id no es CAP-<ULID>"})
            return
        carpeta = f"capturas/{resultado.id_captura}/"
        try:
            self.s3.head_object(Bucket=destino, Key=carpeta + "meta.json")
        except ClientError as exc:
            if _no_existe_objeto(exc):
                logger.info("meta_pendiente", extra={"id_trabajo": resultado.id_trabajo})
                raise MetaPendiente(resultado) from None
            raise
        parte = {"texto": resultado.texto_completo}
        archivo = self._copiar_audio(trabajo, destino, carpeta)
        if archivo:
            parte["archivo"] = archivo
        cuerpo = {"id_captura": resultado.id_captura, "fuente": "audio", "partes": [parte]}
        try:
            # IfNoneMatch: si ya existe no se sobrescribe, así ProcesarNota no procesa dos veces.
            self.s3.put_object(
                Bucket=destino,
                Key=carpeta + "texto.json",
                Body=json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"),
                ContentType="application/json",
                IfNoneMatch="*",
            )
        except ClientError as exc:
            if _codigo(exc) in ("PreconditionFailed", "ConditionalRequestConflict", "412", "409"):
                logger.info("texto_ya_entregado", extra={"id_trabajo": resultado.id_trabajo})
                return
            raise
        logger.info("texto_entregado", extra={"id_trabajo": resultado.id_trabajo, "bucket_destino": destino})

    def _copiar_audio(self, trabajo: dict[str, Any], destino: str, carpeta: str) -> str | None:
        """Copia el audio a capturas/{id}/original/audio.<ext>. Devuelve la ruta relativa, o None si ya no está."""
        clave = self._clave_audio(trabajo)
        if clave is None:
            return None
        relativo = "original/audio." + clave.rsplit(".", 1)[-1]
        try:
            self.s3.copy_object(Bucket=destino, Key=carpeta + relativo, CopySource=f"{self.config.bucket}/{clave}")
        except ClientError as exc:
            if _no_existe_objeto(exc):  # el audio ya no está (por ejemplo, venció a 1 día)
                logger.warning("audio_no_disponible", extra={"id_trabajo": trabajo["TranscriptionJobName"]})
                return None
            raise
        logger.info("audio_copiado", extra={"id_trabajo": trabajo["TranscriptionJobName"], "bucket_destino": destino})
        return relativo

    def _completado(self, trabajo: dict[str, Any]) -> ResultadoTranscripcion:
        id_trabajo = trabajo["TranscriptionJobName"]
        try:
            crudo = self._leer_json(f"transcripciones/{id_trabajo}.json")
        except ClientError as exc:
            if not _no_existe_objeto(exc):
                raise
            return self._fallido(
                trabajo, "resultado_no_disponible", "La transcripción ya no está en S3 (se borra después de un día)"
            )
        try:
            texto, palabras, promedio = convertir_salida(crudo, self.config.umbral_palabra_dudosa)
        except ValueError:
            return self._fallido(trabajo, "resultado_invalido", "No se pudo interpretar la salida de Amazon Transcribe")
        return self._armar(trabajo, "completado", texto=texto, palabras=palabras, promedio=promedio)

    def _fallido(self, trabajo: dict[str, Any], codigo: str, mensaje: str) -> ResultadoTranscripcion:
        return self._armar(trabajo, "fallido", error=ErrorResultado(codigo=codigo, mensaje=mensaje))

    def _armar(
        self,
        trabajo: dict[str, Any],
        estado: str,
        *,
        texto: str = "",
        palabras: list[Palabra] | None = None,
        promedio: float | None = None,
        error: ErrorResultado | None = None,
    ) -> ResultadoTranscripcion:
        id_trabajo = trabajo["TranscriptionJobName"]
        idioma = trabajo.get("LanguageCode")
        return ResultadoTranscripcion(
            id_captura=id_trabajo[len(self.config.prefijo_trabajo):],
            origen="audio",
            estado=estado,
            texto_completo=texto,
            palabras=palabras or [],
            confianza_agregada=promedio,
            idioma=idioma if idioma in IDIOMAS else self.config.idioma,
            proveedor=PROVEEDOR,
            modelo=MODELO,
            id_trabajo=id_trabajo,
            iniciado_en=iso_utc(trabajo.get("CreationTime")),
            terminado_en=None if estado == "transcribiendo" else iso_utc(trabajo.get("CompletionTime")),
            error=error,
        )

    def _estado_actual(self, trabajo: dict[str, Any]) -> ResultadoTranscripcion:
        if trabajo["TranscriptionJobStatus"] in TERMINALES:
            return self.finalizar(trabajo)
        return self._armar(trabajo, "transcribiendo")

    def _resultado_existente(self, trabajo: dict[str, Any]) -> ResultadoTranscripcion:
        if not self._es_propio(trabajo):
            raise IdEnUso(trabajo["TranscriptionJobName"])
        guardado = self._leer_resultado(trabajo["TranscriptionJobName"])
        if guardado is not None:
            return guardado
        try:
            return self._estado_actual(trabajo)
        except MetaPendiente as exc:
            return exc.resultado

    def _es_propio(self, trabajo: dict[str, Any]) -> bool:
        uri = (trabajo.get("Media") or {}).get("MediaFileUri", "")
        return uri.startswith(f"s3://{self.config.bucket}/audio/")

    def _obtener_trabajo(self, id_trabajo: str) -> dict[str, Any] | None:
        try:
            return self.transcribe.get_transcription_job(TranscriptionJobName=id_trabajo)["TranscriptionJob"]
        except ClientError as exc:
            if _no_existe_trabajo(exc):
                return None
            raise

    def _leer_resultado(self, id_trabajo: str) -> ResultadoTranscripcion | None:
        try:
            return ResultadoTranscripcion.model_validate(self._leer_json(f"resultados/{id_trabajo}.json"))
        except ClientError as exc:
            if _no_existe_objeto(exc):
                return None
            raise

    def _leer_json(self, clave: str) -> Any:
        respuesta = self.s3.get_object(Bucket=self.config.bucket, Key=clave)
        return json.loads(respuesta["Body"].read())

    def _clave_audio(self, trabajo: dict[str, Any]) -> str | None:
        """Clave del audio del trabajo en este bucket (audio/...), o None si no es de este servicio."""
        prefijo = f"s3://{self.config.bucket}/"
        uri = (trabajo.get("Media") or {}).get("MediaFileUri", "")
        return uri[len(prefijo):] if uri.startswith(prefijo + "audio/") else None

    def _borrar_audio(self, trabajo: dict[str, Any]) -> None:
        clave = self._clave_audio(trabajo)
        if clave is None:
            return
        try:
            self.s3.delete_object(Bucket=self.config.bucket, Key=clave)
        except ClientError as exc:  # la regla de ciclo de vida del bucket lo borra igual
            logger.warning(
                "audio_no_borrado", extra={"id_trabajo": trabajo["TranscriptionJobName"], "codigo_aws": _codigo(exc)}
            )


class ServicioMock:
    """Respuestas simuladas para integrar sin AWS (proveedor "mock"). No entrega texto.json.

    POST responde "transcribiendo". GET responde "completado" con un texto de ejemplo,
    "fallido" si el id contiene "fallido" y "transcribiendo" si contiene "transcribiendo".
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        ruta = resources.files("transcriptor").joinpath("datos").joinpath("ejemplo_transcribe.json")
        self._ejemplo = json.loads(ruta.read_text(encoding="utf-8"))

    def iniciar(
        self, id_captura: str, audio: bytes, formato: FormatoAudio, idioma: str | None = None
    ) -> ResultadoTranscripcion:
        return self._resultado(self.config.prefijo_trabajo + id_captura, "transcribiendo", idioma)

    def consultar(self, id_trabajo: str, exigir_entrega: bool = False) -> ResultadoTranscripcion | None:
        prefijo = self.config.prefijo_trabajo
        if not id_trabajo.startswith(prefijo) or id_trabajo == prefijo:
            return None
        if "fallido" in id_trabajo:
            return self._resultado(id_trabajo, "fallido")
        if "transcribiendo" in id_trabajo:
            return self._resultado(id_trabajo, "transcribiendo")
        return self._resultado(id_trabajo, "completado")

    def _resultado(self, id_trabajo: str, estado: str, idioma: str | None = None) -> ResultadoTranscripcion:
        ahora = datetime.now(timezone.utc)
        texto, palabras, promedio = "", [], None
        if estado == "completado":
            texto, palabras, promedio = convertir_salida(self._ejemplo, self.config.umbral_palabra_dudosa)
        error = None
        if estado == "fallido":
            error = ErrorResultado(codigo="transcripcion_fallida", mensaje="Fallo simulado (modo mock)")
        return ResultadoTranscripcion(
            id_captura=id_trabajo[len(self.config.prefijo_trabajo):],
            origen="audio",
            estado=estado,
            texto_completo=texto,
            palabras=palabras,
            confianza_agregada=promedio,
            idioma=idioma or self.config.idioma,
            proveedor="mock",
            modelo="mock",
            id_trabajo=id_trabajo,
            iniciado_en=iso_utc(ahora - timedelta(seconds=30)),
            terminado_en=None if estado == "transcribiendo" else iso_utc(ahora),
            error=error,
        )


_servicio: ServicioTranscribe | ServicioMock | None = None


def obtener_servicio() -> ServicioTranscribe | ServicioMock:
    """Crea el servicio una vez por proceso (en Lambda se reutiliza entre invocaciones)."""
    global _servicio
    if _servicio is None:
        config = cargar_config()
        if config.modo_mock:
            _servicio = ServicioMock(config)
        else:
            import boto3
            from botocore.config import Config as ConfigBoto

            ajustes = ConfigBoto(connect_timeout=3, read_timeout=8, retries={"max_attempts": 2, "mode": "standard"})
            _servicio = ServicioTranscribe(
                config, boto3.client("s3", config=ajustes), boto3.client("transcribe", config=ajustes)
            )
    return _servicio


def configurar_servicio(servicio: ServicioTranscribe | ServicioMock | None) -> None:
    """Reemplaza el servicio. Lo usan las pruebas."""
    global _servicio
    _servicio = servicio