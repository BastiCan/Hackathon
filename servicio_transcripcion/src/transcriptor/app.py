"""API HTTP del transcriptor. En AWS la expone Mangum detrás de API Gateway REST."""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Annotated, Any

from botocore.exceptions import BotoCoreError, ClientError, ConnectTimeoutError, ReadTimeoutError
from fastapi import FastAPI, Path, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from mangum import Mangum
from starlette.exceptions import HTTPException as StarletteHTTPException

from .audio import AudioInvalido, decodificar_base64, detectar_formato
from .contrato import PATRON_ID_TRABAJO, RespuestaError, ResultadoTranscripcion, SolicitudAudio
from .servicio import IdEnUso, ServicioMock, ServicioTranscribe, obtener_servicio

logger = logging.getLogger("transcriptor")

SATURACION = {"ThrottlingException", "LimitExceededException", "SlowDown", "TooManyRequestsException"}
ERRORES: dict[int | str, dict[str, Any]] = {
    codigo: {"model": RespuestaError} for codigo in (400, 404, 409, 413, 415, 422, 500, 502, 503, 504)
}


class ErrorServicio(Exception):
    def __init__(self, estado_http: int, codigo: str, mensaje: str, cabeceras: dict[str, str] | None = None) -> None:
        super().__init__(mensaje)
        self.estado_http = estado_http
        self.codigo = codigo
        self.mensaje = mensaje
        self.cabeceras = cabeceras


app = FastAPI(
    title="Transcriptor de audio",
    version="1.0.0",
    description="Audio a texto con Amazon Transcribe por lotes. Contrato: contrato/resultado_transcripcion.schema.json",
)


def _respuesta_error(estado_http: int, codigo: str, mensaje: str, cabeceras: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(status_code=estado_http, content={"error": {"codigo": codigo, "mensaje": mensaje}}, headers=cabeceras)


@app.exception_handler(ErrorServicio)
async def _error_servicio(_: Request, exc: ErrorServicio) -> JSONResponse:
    return _respuesta_error(exc.estado_http, exc.codigo, exc.mensaje, exc.cabeceras)


@app.exception_handler(RequestValidationError)
async def _error_validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
    detalles = "; ".join(
        f"{'.'.join(str(parte) for parte in error['loc'][1:]) or 'cuerpo'}: {error['msg']}" for error in exc.errors()
    )
    return _respuesta_error(422, "solicitud_invalida", detalles or "Solicitud inválida")


@app.exception_handler(StarletteHTTPException)
async def _error_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    codigo = {404: "no_encontrado", 405: "metodo_no_permitido"}.get(exc.status_code, "error_http")
    return _respuesta_error(exc.status_code, codigo, str(exc.detail))


def _servicio() -> ServicioTranscribe | ServicioMock:
    try:
        return obtener_servicio()
    except ValueError as exc:
        logger.error("configuracion_invalida", extra={"detalle": str(exc)})
        raise ErrorServicio(500, "configuracion_invalida", str(exc)) from None


def _llamar(funcion: Callable[..., Any], *args: Any) -> Any:
    """Ejecuta una operación del servicio y traduce los errores de AWS a respuestas HTTP."""
    try:
        return funcion(*args)
    except IdEnUso:
        raise ErrorServicio(409, "id_en_uso", "Otro trabajo de Transcribe de la cuenta ya usa ese id_captura") from None
    except (ReadTimeoutError, ConnectTimeoutError):
        logger.warning("aws_tiempo_agotado")
        raise ErrorServicio(504, "tiempo_agotado", "AWS no respondió a tiempo. Reintente") from None
    except ClientError as exc:
        codigo_aws = exc.response.get("Error", {}).get("Code", "desconocido")
        logger.warning("aws_error", extra={"codigo_aws": codigo_aws, "operacion": exc.operation_name})
        if codigo_aws in SATURACION:
            raise ErrorServicio(
                503, "servicio_saturado", "AWS está limitando las solicitudes. Reintente", {"Retry-After": "5"}
            ) from None
        raise ErrorServicio(502, "error_proveedor", f"AWS respondió {codigo_aws}") from None
    except BotoCoreError as exc:
        logger.warning("aws_sin_conexion", extra={"tipo_error": type(exc).__name__})
        raise ErrorServicio(502, "error_proveedor", "No se pudo contactar a AWS") from None


@app.get("/api/salud")
def salud() -> dict[str, str]:
    return {"estado": "ok", "modo": "mock" if _servicio().config.modo_mock else "aws"}


@app.post(
    "/api/transcripciones/audio",
    status_code=202,
    response_model=ResultadoTranscripcion,
    responses={200: {"model": ResultadoTranscripcion, "description": "Ese id_captura ya tenía resultado final"}, **ERRORES},
)
def crear_transcripcion(solicitud: SolicitudAudio, response: Response) -> ResultadoTranscripcion:
    servicio = _servicio()
    try:
        audio = decodificar_base64(solicitud.audio_base64, servicio.config.max_bytes_audio)
    except AudioInvalido as exc:
        raise ErrorServicio(exc.estado_http, exc.codigo, exc.mensaje) from None
    formato = detectar_formato(audio)
    if formato is None:
        raise ErrorServicio(415, "formato_no_soportado", "Formatos aceptados: webm, ogg, mp4/m4a, mp3, wav, flac y amr")
    resultado = _llamar(servicio.iniciar, solicitud.id_captura, audio, formato, solicitud.idioma)
    if resultado.estado != "transcribiendo":
        response.status_code = 200
    return resultado


@app.get("/api/transcripciones/{id_trabajo}", response_model=ResultadoTranscripcion, responses=ERRORES)
def consultar_transcripcion(id_trabajo: Annotated[str, Path(pattern=PATRON_ID_TRABAJO)]) -> ResultadoTranscripcion:
    resultado = _llamar(_servicio().consultar, id_trabajo)
    if resultado is None:
        raise ErrorServicio(404, "trabajo_no_encontrado", f"No existe la transcripción {id_trabajo}")
    return resultado


handler = Mangum(app, lifespan="off")