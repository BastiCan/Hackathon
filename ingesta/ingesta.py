"""Lambda integra-ingesta: entrada única de fotos y audios de una captura.

Rutas (API Gateway REST, integración proxy, exige x-api-key):
  POST /capturas                 valida educadora y sala, genera CAP-<ULID> y firma la subida (no escribe nada)
  POST /capturas/{id}/procesar   decide foto o audio por los bytes, escribe meta.json y llama a la herramienta:
                                 foto -> Lambda postits-ocr (síncrona); audio -> API del transcriptor
  GET  /capturas/{id}            estado en Registros y observaciones de la captura

Solo lee DynamoDB. En S3 solo escribe capturas/{id}/meta.json (el archivo lo sube el cliente con la URL firmada).
Las tablas las actualiza ProcesarNota del equipo cuando aparecen meta.json y texto.json.
Logs: ids, tipos, códigos y tiempos; nunca textos, nombres ni la clave del transcriptor.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import logging
import os
import re
import time
import traceback
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.config import Config
from botocore.exceptions import ClientError, ParamValidationError, ReadTimeoutError
from ulid import ULID


def _cargar_capturas_equipo():
    """Validador del equipo (integra-backend/src/core/capturas.py): del repo o la copia del zip."""
    ruta = Path(__file__).resolve().parents[1] / "integra-backend" / "src" / "core" / "capturas.py"
    if ruta.is_file():
        spec = importlib.util.spec_from_file_location("capturas_equipo", ruta)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return modulo
    import capturas_equipo  # copia del zip de Lambda
    return capturas_equipo


capturas_equipo = _cargar_capturas_equipo()

log = logging.getLogger()
log.setLevel(logging.INFO)

BUCKET = os.environ.get("BUCKET_CAPTURAS", "integra-capturas-277702547089")
TABLA_EDUCADORAS = os.environ.get("TABLA_EDUCADORAS", "integra-procesador-TablaEducadoras-PMJ55I44WU75")
TABLA_NINOS = os.environ.get("TABLA_NINOS", "integra-procesador-TablaNinos-11AMEMFM7SFST")
TABLA_REGISTROS = os.environ.get("TABLA_REGISTROS", "integra-procesador-TablaRegistros-P238ZZKPTQ51")
TABLA_OBSERVACIONES = os.environ.get("TABLA_OBSERVACIONES", "integra-procesador-TablaObservaciones-1MP6ZR2QT9JAU")
FUNCION_OCR = os.environ.get("FUNCION_OCR", "postits-ocr")
URL_TRANSCRIPTOR = os.environ.get("URL_TRANSCRIPTOR", "https://289khkzbpd.execute-api.us-east-1.amazonaws.com/v1")
ID_CLAVE_TRANSCRIPTOR = os.environ.get("ID_CLAVE_TRANSCRIPTOR", "14b8weklf1")

EXPIRA_S = 900                      # URL de subida: 15 minutos
MAX_AUDIO = 4 * 1024 * 1024         # límite del transcriptor
MAX_FOTO = 25 * 1024 * 1024         # límite de postits-ocr
ESPERA_OCR_S = 22                   # menos que los 29 s de API Gateway
ESPERA_TRANSCRIPTOR_S = 20
FECHA_MIN = date(2020, 1, 1)

_RE_ID = re.compile(r"^CAP-[0-9A-HJKMNP-TV-Z]{26}$")  # el mismo del equipo
_RE_CAMPO = re.compile(r"[A-Za-z0-9_-]{1,64}")
_RE_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")
_RE_CONTENT_TYPE = re.compile(r"[A-Za-z0-9.+-]{1,40}/[A-Za-z0-9.+-]{1,60}")

# Extensión de la subida, por nombre de archivo o por content_type.
_EXTENSIONES = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "wav": "wav", "ogg": "ogg", "oga": "ogg", "opus": "ogg",
                "webm": "webm", "m4a": "m4a", "mp4": "mp4", "mp3": "mp3", "flac": "flac", "amr": "amr"}
_CONTENT_TYPES = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png",
                  "audio/wav": "wav", "audio/x-wav": "wav", "audio/wave": "wav", "audio/vnd.wave": "wav",
                  "audio/ogg": "ogg", "audio/opus": "ogg", "audio/webm": "webm", "video/webm": "webm",
                  "audio/mp4": "m4a", "audio/m4a": "m4a", "audio/x-m4a": "m4a", "video/mp4": "mp4",
                  "audio/mpeg": "mp3", "audio/mp3": "mp3", "audio/flac": "flac", "audio/x-flac": "flac",
                  "audio/amr": "amr"}
_HEIF = {"heic", "heif", "image/heic", "image/heif", "image/heic-sequence", "image/heif-sequence"}
# Marcas ftyp de imágenes HEIF/AVIF (no son audio aunque usen el contenedor ISO).
_MARCAS_HEIF = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"hevm", b"hevs", b"mif1", b"msf1",
                b"avif", b"avis"}

CAMPOS_OBS = ("id_obs", "id_nino", "tipo", "error_identificacion", "candidatos", "evaluabilidad", "nivel", "certeza",
              "estado", "texto_literal", "archivo_s3")

_clientes: dict = {}
_clave_transcriptor: str | None = None  # solo en memoria, nunca en logs ni respuestas


class ErrorApi(Exception):
    def __init__(self, http: int, codigo: str, mensaje: str, **extra):
        super().__init__(codigo)
        self.http, self.codigo, self.mensaje, self.extra = http, codigo, mensaje, extra

    def cuerpo(self) -> dict:
        return {"error": {"codigo": self.codigo, "mensaje": self.mensaje}, **self.extra}


# ----------------------------------------------------------------------------- clientes

def _s3():
    if "s3" not in _clientes:
        _clientes["s3"] = boto3.client("s3", config=Config(signature_version="s3v4",
                                                           s3={"addressing_style": "virtual"}))
    return _clientes["s3"]


def _tabla(nombre: str):
    if "ddb" not in _clientes:
        _clientes["ddb"] = boto3.resource("dynamodb")
    return _clientes["ddb"].Table(nombre)


def _lambda():
    if "lambda" not in _clientes:
        _clientes["lambda"] = boto3.client("lambda", config=Config(
            read_timeout=ESPERA_OCR_S, connect_timeout=3, retries={"max_attempts": 0}))
    return _clientes["lambda"]


def _clave_api_transcriptor() -> str:
    global _clave_transcriptor
    if _clave_transcriptor is None:
        if "apigw" not in _clientes:
            _clientes["apigw"] = boto3.client("apigateway")
        _clave_transcriptor = _clientes["apigw"].get_api_key(apiKey=ID_CLAVE_TRANSCRIPTOR, includeValue=True)["value"]
    return _clave_transcriptor


# ----------------------------------------------------------------------------- validaciones

def hoy_chile() -> date:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Santiago")).date()
    except Exception:  # runtime sin base de zonas: regla de Chile (UTC-3 de septiembre a abril, si no UTC-4)
        local = datetime.now(timezone.utc) - timedelta(hours=4)
        f = local.date()

        def primer_domingo(anio: int, mes: int) -> date:
            d = date(anio, mes, 1)
            return d + timedelta(days=(6 - d.weekday()) % 7)

        verano = not (primer_domingo(f.year, 4) <= f < primer_domingo(f.year, 9))
        return (local + timedelta(hours=1)).date() if verano else f


def es_id_valido(valor) -> bool:
    return isinstance(valor, str) and _RE_ID.fullmatch(valor) is not None and capturas_equipo.es_id_captura(valor)


def nuevo_id_captura() -> str:
    id_captura = f"CAP-{ULID()}"
    if not es_id_valido(id_captura):  # no debería pasar: mismo alfabeto Crockford
        raise RuntimeError("python-ulid genero un id que el equipo no acepta")
    return id_captura


def _campo(d: dict, campo: str, obligatorio: bool = True) -> str | None:
    valor = d.get(campo)
    if valor is None and not obligatorio:
        return None
    if not isinstance(valor, str) or _RE_CAMPO.fullmatch(valor) is None:
        raise ErrorApi(400, "PETICION_INVALIDA", f"campo invalido: {campo}")
    return valor


def _fecha(valor) -> date:
    if valor is None:
        return hoy_chile()
    if not isinstance(valor, str) or _RE_FECHA.fullmatch(valor) is None:
        raise ErrorApi(400, "PETICION_INVALIDA", "campo invalido: fecha_observacion (AAAA-MM-DD)")
    try:
        fecha = date.fromisoformat(valor)
    except ValueError:
        raise ErrorApi(400, "PETICION_INVALIDA", "campo invalido: fecha_observacion (AAAA-MM-DD)") from None
    if not FECHA_MIN <= fecha <= hoy_chile():
        raise ErrorApi(400, "PETICION_INVALIDA", "fecha_observacion fuera de rango (2020-01-01 a hoy)")
    return fecha


def extension(nombre_archivo, content_type) -> str:
    """Extensión de la subida. 415 si es HEIC/HEIF o un formato que ninguna herramienta acepta."""
    if nombre_archivo is None and content_type is None:
        raise ErrorApi(400, "PETICION_INVALIDA", "falta nombre_archivo o content_type")
    if nombre_archivo is not None and (not isinstance(nombre_archivo, str) or not 0 < len(nombre_archivo) <= 255):
        raise ErrorApi(400, "PETICION_INVALIDA", "campo invalido: nombre_archivo")
    if content_type is not None and (not isinstance(content_type, str)
                                     or _RE_CONTENT_TYPE.fullmatch(content_type) is None):
        raise ErrorApi(400, "PETICION_INVALIDA", "campo invalido: content_type (tipo/subtipo, sin parametros)")
    ext_nombre = nombre_archivo.rsplit(".", 1)[-1].lower() if nombre_archivo and "." in nombre_archivo else None
    ct = content_type.lower() if content_type else None
    if ext_nombre in _HEIF or ct in _HEIF:
        raise ErrorApi(415, "FORMATO_NO_SOPORTADO", "HEIC/HEIF no soportado: convertir a JPEG")
    ext = _EXTENSIONES.get(ext_nombre) or _CONTENT_TYPES.get(ct)
    if ext is None:
        raise ErrorApi(415, "FORMATO_NO_SOPORTADO",
                       "formatos: jpg, png, wav, ogg, webm, m4a, mp4, mp3, flac o amr")
    return ext


def validar_educadora_y_sala(id_educadora: str, sala_grupo: str, fecha: date) -> str:
    """Las mismas reglas que ProcesarNota: la educadora existe y la sala tiene niños con fecha_ingreso <= fecha."""
    item = _tabla(TABLA_EDUCADORAS).get_item(Key={"id_educadora": id_educadora},
                                             ProjectionExpression="id_jardin").get("Item") or {}
    id_jardin = item.get("id_jardin")
    if not isinstance(id_jardin, str) or not id_jardin:
        raise ErrorApi(400, "EDUCADORA_DESCONOCIDA", "id_educadora no existe en Educadoras")
    kw = {"KeyConditionExpression": Key("id_jardin").eq(id_jardin),
          "FilterExpression": Attr("sala_grupo").eq(sala_grupo) & Attr("fecha_ingreso").lte(fecha.isoformat()),
          "ProjectionExpression": "id_nino"}
    while True:
        r = _tabla(TABLA_NINOS).query(**kw)
        if r.get("Count"):
            return id_jardin
        if "LastEvaluatedKey" not in r:
            raise ErrorApi(400, "SALA_DESCONOCIDA", "la sala no tiene ninos del jardin de la educadora en esa fecha")
        kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]


def detectar_tipo(b: bytes) -> tuple[str | None, str]:
    """(tipo, formato) por la firma de los primeros bytes. tipo es "foto", "audio" o None (no soportado)."""
    if b.startswith(b"\xff\xd8\xff"):
        return "foto", "jpeg"
    if b.startswith(b"\x89PNG"):
        return "foto", "png"
    if len(b) >= 12 and b[4:8] == b"ftyp":
        if b[8:12].lower() in _MARCAS_HEIF:
            return None, "heif"
        return "audio", "mp4"
    if b.startswith(b"RIFF") and b[8:12] == b"WAVE":
        return "audio", "wav"
    if b.startswith(b"OggS"):
        return "audio", "ogg"
    if b.startswith(b"\x1a\x45\xdf\xa3"):
        return "audio", "webm"
    if b.startswith(b"ID3") or b[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "audio", "mp3"
    if b.startswith(b"fLaC"):
        return "audio", "flac"
    if b.startswith(b"#!AMR"):
        return "audio", "amr"
    return None, "desconocido"


# ----------------------------------------------------------------------------- rutas

def crear_captura(d: dict) -> tuple[int, dict]:
    id_educadora = _campo(d, "id_educadora")
    sala_grupo = _campo(d, "sala_grupo")
    fecha = _fecha(d.get("fecha_observacion"))
    ext = extension(d.get("nombre_archivo"), d.get("content_type"))
    validar_educadora_y_sala(id_educadora, sala_grupo, fecha)
    id_captura = nuevo_id_captura()
    clave = capturas_equipo.clave_archivo(id_captura, f"original/subida.{ext}")
    # Los datos viajan firmados en la URL como metadatos del objeto: /procesar los lee de ahí.
    metadatos = {"educadora": id_educadora, "sala": sala_grupo, "fecha": fecha.isoformat()}
    params = {"Bucket": BUCKET, "Key": clave, "Metadata": metadatos}
    cabeceras = {f"x-amz-meta-{k}": v for k, v in metadatos.items()}
    if d.get("content_type"):
        params["ContentType"] = d["content_type"]
        cabeceras["Content-Type"] = d["content_type"]
    url = _s3().generate_presigned_url("put_object", Params=params, ExpiresIn=EXPIRA_S)
    log.info(json.dumps({"evento": "captura_creada", "id_captura": id_captura, "ext": ext}))
    return 200, {"id_captura": id_captura, "clave": clave, "url_subida": url, "expira_s": EXPIRA_S,
                 "metodo": "PUT", "cabeceras": cabeceras, "fecha_observacion": fecha.isoformat()}


def _listar(prefijo: str) -> dict[str, int]:
    claves, kw = {}, {"Bucket": BUCKET, "Prefix": prefijo}
    while True:
        r = _s3().list_objects_v2(**kw)
        claves.update({o["Key"]: o["Size"] for o in r.get("Contents", [])})
        if not r.get("IsTruncated"):
            return claves
        kw["ContinuationToken"] = r["NextContinuationToken"]


def _datos_captura(d: dict, metadatos: dict) -> tuple[str, str, date]:
    """Educadora, sala y fecha: los firmados en la subida; si el cuerpo trae otro valor, 409."""
    valores = {}
    for campo, meta in (("id_educadora", "educadora"), ("sala_grupo", "sala"), ("fecha_observacion", "fecha")):
        del_cuerpo, de_subida = d.get(campo), metadatos.get(meta)
        if del_cuerpo is not None and de_subida is not None and del_cuerpo != de_subida:
            raise ErrorApi(409, "DATOS_NO_COINCIDEN", f"{campo} no coincide con el de la subida")
        valores[campo] = del_cuerpo if del_cuerpo is not None else de_subida
    for campo in ("id_educadora", "sala_grupo"):
        if valores[campo] is None:
            raise ErrorApi(400, "PETICION_INVALIDA", f"falta {campo} (la subida no lo trae)")
    return (_campo(valores, "id_educadora"), _campo(valores, "sala_grupo"),
            _fecha(valores["fecha_observacion"]))


def _escribir_meta(clave: str, meta: dict) -> bool:
    """meta.json solo si no existe. True si esta llamada lo escribió."""
    cuerpo = json.dumps(meta, ensure_ascii=False).encode("utf-8")
    args = {"Bucket": BUCKET, "Key": clave, "Body": cuerpo, "ContentType": "application/json; charset=utf-8",
            "Metadata": {"origen": "integra-ingesta"}}
    try:
        _s3().put_object(IfNoneMatch="*", **args)
        return True
    except ParamValidationError:  # boto3 del runtime sin escritura condicional
        log.warning(json.dumps({"evento": "escritura_no_condicional"}))
        if clave in _listar(clave):
            return False
        _s3().put_object(**args)
        return True
    except ClientError as e:
        codigo = e.response.get("Error", {}).get("Code", "")
        http = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if codigo in ("PreconditionFailed", "ConditionalRequestConflict") or http in (409, 412):
            return False
        raise


def _llamar_ocr(id_captura: str, clave: str) -> tuple[int, dict]:
    t = time.monotonic()
    try:
        r = _lambda().invoke(FunctionName=FUNCION_OCR, InvocationType="RequestResponse",
                             Payload=json.dumps({"id_captura": id_captura, "s3_key": clave}).encode())
    except ReadTimeoutError:  # postits-ocr sigue corriendo y escribirá texto.json
        log.warning(json.dumps({"evento": "ocr_sigue", "id_captura": id_captura}))
        return 202, {"estado": "en_proceso", "mensaje": "postits-ocr sigue trabajando: consulte GET /capturas/{id}"}
    crudo = r["Payload"].read()
    ms = int((time.monotonic() - t) * 1000)
    try:
        cuerpo = json.loads(crudo or b"null")
    except ValueError:
        cuerpo = None
    if r.get("FunctionError") or not isinstance(cuerpo, dict):
        log.error(json.dumps({"evento": "ocr_fallo", "id_captura": id_captura, "ms": ms}))
        raise ErrorApi(502, "HERRAMIENTA_FALLO", "postits-ocr fallo (FunctionError o respuesta invalida)")
    if isinstance(cuerpo.get("error"), dict):
        codigo = str(cuerpo["error"].get("codigo") or "ERROR_HERRAMIENTA")
        http = {"FORMATO_NO_SOPORTADO": 415, "IMAGEN_NO_DECODIFICABLE": 415, "IMAGEN_DEMASIADO_GRANDE": 413,
                "IMAGEN_NO_ENCONTRADA": 404, "PETICION_INVALIDA": 409, "META_INVALIDA": 409}.get(codigo, 502)
        log.warning(json.dumps({"evento": "ocr_error", "id_captura": id_captura, "codigo": codigo, "ms": ms}))
        raise ErrorApi(http, codigo, str(cuerpo["error"].get("mensaje") or "error de postits-ocr"))
    log.info(json.dumps({"evento": "ocr_ok", "id_captura": id_captura, "n_postits": cuerpo.get("n_postits"),
                         "avisos": [str(a).split(":")[0] for a in cuerpo.get("avisos", [])], "ms": ms}))
    partes = [{k: p.get(k) for k in ("orden", "archivo", "texto", "legibilidad")} for p in cuerpo.get("partes", [])]
    return 200, {"n_postits": cuerpo.get("n_postits"), "partes": partes, "texto_escrito": cuerpo.get("texto_escrito"),
                 "tiempos_ms": cuerpo.get("tiempos_ms"), "avisos": cuerpo.get("avisos", [])}


def _llamar_transcriptor(id_captura: str, clave: str) -> tuple[int, dict]:
    global _clave_transcriptor
    audio = _s3().get_object(Bucket=BUCKET, Key=clave)["Body"].read()
    if len(audio) > MAX_AUDIO:
        raise ErrorApi(413, "AUDIO_DEMASIADO_GRANDE", "el audio pasa de 4 MiB")
    cuerpo = json.dumps({"id_captura": id_captura, "audio_base64": base64.b64encode(audio).decode("ascii"),
                         "idioma": "es-US"}).encode("utf-8")
    peticion = urllib.request.Request(
        URL_TRANSCRIPTOR.rstrip("/") + "/api/transcripciones/audio", data=cuerpo, method="POST",
        headers={"Content-Type": "application/json", "x-api-key": _clave_api_transcriptor()})
    t = time.monotonic()
    try:
        with urllib.request.urlopen(peticion, timeout=ESPERA_TRANSCRIPTOR_S) as r:
            http, crudo = r.status, r.read()
    except urllib.error.HTTPError as e:
        http, crudo = e.code, e.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        log.error(json.dumps({"evento": "transcriptor_sin_respuesta", "id_captura": id_captura,
                              "tipo_error": type(e).__name__}))
        raise ErrorApi(502, "TRANSCRIPTOR_NO_RESPONDE", "el transcriptor no respondio: reintentar") from None
    ms = int((time.monotonic() - t) * 1000)
    try:
        respuesta = json.loads(crudo or b"null")
    except ValueError:
        respuesta = None
    if http in (200, 202) and isinstance(respuesta, dict):
        log.info(json.dumps({"evento": "transcriptor_ok", "id_captura": id_captura, "http": http,
                             "estado": respuesta.get("estado"), "bytes": len(audio), "ms": ms}))
        return http, {k: respuesta.get(k) for k in ("estado", "id_trabajo", "texto_completo", "confianza_agregada",
                                                     "idioma", "error")}
    codigo = None
    if isinstance(respuesta, dict) and isinstance(respuesta.get("error"), dict):
        codigo = respuesta["error"].get("codigo")
    if http == 403:
        _clave_transcriptor = None  # quizás rotó: se vuelve a leer en la próxima llamada
    log.warning(json.dumps({"evento": "transcriptor_rechazo", "id_captura": id_captura, "http": http,
                            "codigo": codigo, "ms": ms}))
    raise ErrorApi({409: 409, 413: 413, 415: 415}.get(http, 502), "TRANSCRIPTOR_RECHAZO",
                   f"el transcriptor respondio {http} ({codigo or 'sin codigo'})")


def procesar(id_captura: str, d: dict) -> tuple[int, dict]:
    escribir = d.get("escribir", True)
    if type(escribir) is not bool:
        raise ErrorApi(400, "PETICION_INVALIDA", "campo invalido: escribir (true o false)")
    prefijo = capturas_equipo.clave_archivo(id_captura, "")
    objetos = _listar(prefijo)
    subidas = sorted(k for k in objetos if k.startswith(prefijo + "original/subida."))
    if not subidas:
        raise ErrorApi(404, "ARCHIVO_NO_ENCONTRADO", "no hay original/subida.* en la captura: subir primero")
    if len(subidas) > 1:
        raise ErrorApi(409, "VARIAS_SUBIDAS", "la captura tiene mas de un original/subida.*")
    clave = subidas[0]
    if prefijo + "texto.json" in objetos:
        raise ErrorApi(409, "YA_PROCESADA", "la captura ya tiene texto.json")
    total = objetos[clave]
    if total == 0:
        raise ErrorApi(415, "FORMATO_NO_SOPORTADO", "el archivo esta vacio")
    r = _s3().get_object(Bucket=BUCKET, Key=clave, Range="bytes=0-63")
    cabecera, metadatos = r["Body"].read(), r.get("Metadata") or {}
    tipo, formato = detectar_tipo(cabecera)
    base = {"id_captura": id_captura, "tipo": tipo, "formato": formato}
    if tipo is None:
        raise ErrorApi(415, "FORMATO_NO_SOPORTADO", f"formato {formato}: se aceptan JPEG, PNG o audio", **base)
    herramienta = "postits-ocr" if tipo == "foto" else "transcriptor"
    base["herramienta"] = herramienta
    if tipo == "foto" and not clave.lower().endswith((".jpg", ".jpeg", ".png")):
        raise ErrorApi(415, "EXTENSION_NO_CORRESPONDE", "el archivo es una foto pero se subio con extension de audio",
                       **base)
    if tipo == "foto" and total > MAX_FOTO:
        raise ErrorApi(413, "IMAGEN_DEMASIADO_GRANDE", "la foto pasa de 25 MiB", **base)
    if tipo == "audio" and total > MAX_AUDIO:
        raise ErrorApi(413, "AUDIO_DEMASIADO_GRANDE", "el audio pasa de 4 MiB", **base)
    id_educadora, sala_grupo, fecha = _datos_captura(d, metadatos)
    validar_educadora_y_sala(id_educadora, sala_grupo, fecha)
    meta = {"id_educadora": id_educadora, "sala_grupo": sala_grupo, "fecha_observacion": fecha.isoformat(),
            "tipo": tipo}
    clave_meta = prefijo + "meta.json"
    log.info(json.dumps({"evento": "procesar", "id_captura": id_captura, "tipo": tipo, "formato": formato,
                         "bytes": total, "escribir": escribir}))
    if not escribir:
        return 200, {**base, "meta_escrito": False, "resultado": {
            "ensayo": True, "clave": clave, "bytes": total, "meta_existe": clave_meta in objetos, "meta": meta,
            "haria": ["escribir meta.json si no existe",
                      f"invocar {FUNCION_OCR} con s3_key" if tipo == "foto"
                      else "POST /api/transcripciones/audio al transcriptor"]}}
    meta_escrito = _escribir_meta(clave_meta, meta)
    base["meta_escrito"] = meta_escrito
    try:
        if tipo == "foto":
            http, resultado = _llamar_ocr(id_captura, clave)
        else:
            http, resultado = _llamar_transcriptor(id_captura, clave)
    except ErrorApi as e:
        e.extra = {**base, **e.extra}
        raise
    return http, {**base, "resultado": resultado}


def _orden_obs(fila: dict) -> tuple:
    try:
        return tuple(int(x) for x in fila["id_obs"].rsplit("-p", 1)[1].split("-"))
    except (KeyError, IndexError, ValueError):
        return (10 ** 9, 0)


def consultar(id_captura: str) -> tuple[int, dict]:
    registro = _tabla(TABLA_REGISTROS).get_item(Key={"id_captura": id_captura}).get("Item") or {}
    filas, kw = [], {"KeyConditionExpression": Key("id_captura").eq(id_captura)}
    while True:
        r = _tabla(TABLA_OBSERVACIONES).query(**kw)
        filas += r.get("Items", [])
        if "LastEvaluatedKey" not in r:
            break
        kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]
    errores = list(registro.get("errores") or [])
    if registro.get("error"):
        errores.insert(0, {"n_parte": None, "error": registro["error"]})
    observaciones = [{c: f.get(c) for c in CAMPOS_OBS} for f in sorted(filas, key=_orden_obs)]
    return 200, {"id_captura": id_captura, "estado": registro.get("estado"), "errores": errores,
                 "observaciones": observaciones}


# ----------------------------------------------------------------------------- handler

def _cuerpo(event: dict, opcional: bool = False) -> dict:
    crudo = event.get("body")
    if crudo is None or crudo == "":
        if opcional:
            return {}
        raise ErrorApi(400, "PETICION_INVALIDA", "falta el cuerpo JSON")
    try:
        if event.get("isBase64Encoded"):
            crudo = base64.b64decode(crudo).decode("utf-8")
        d = json.loads(crudo) if isinstance(crudo, str) else crudo
    except (ValueError, UnicodeDecodeError):
        raise ErrorApi(400, "PETICION_INVALIDA", "el cuerpo no es JSON") from None
    if not isinstance(d, dict):
        raise ErrorApi(400, "PETICION_INVALIDA", "el cuerpo debe ser un objeto JSON")
    return d


def _id_ruta(event: dict) -> str:
    id_captura = (event.get("pathParameters") or {}).get("id")
    if not es_id_valido(id_captura):
        raise ErrorApi(400, "ID_INVALIDO", "id_captura debe ser CAP-<ULID>")
    return id_captura


def _json(valor):
    if isinstance(valor, Decimal):
        return int(valor) if valor == valor.to_integral_value() else float(valor)
    if isinstance(valor, (set, frozenset)):
        return sorted(valor)
    raise TypeError(type(valor).__name__)


def handler(event, context):
    t0 = time.monotonic()
    metodo, recurso = event.get("httpMethod"), event.get("resource")
    try:
        if metodo == "POST" and recurso == "/capturas":
            http, cuerpo = crear_captura(_cuerpo(event))
        elif metodo == "POST" and recurso == "/capturas/{id}/procesar":
            http, cuerpo = procesar(_id_ruta(event), _cuerpo(event, opcional=True))
        elif metodo == "GET" and recurso == "/capturas/{id}":
            http, cuerpo = consultar(_id_ruta(event))
        else:
            raise ErrorApi(404, "RUTA_NO_ENCONTRADA", "ruta no encontrada")
    except ErrorApi as e:
        http, cuerpo = e.http, e.cuerpo()
    except ClientError as e:
        codigo = e.response.get("Error", {}).get("Code", "")
        log.error(json.dumps({"evento": "error_aws", "codigo": codigo, "operacion": e.operation_name}))
        http, cuerpo = 502, {"error": {"codigo": "ERROR_AWS", "mensaje": f"fallo {e.operation_name} ({codigo})"}}
    except Exception as e:  # bug: sin traceback en la respuesta; en el log solo tipo y líneas
        donde = [f"{Path(f.filename).name}:{f.lineno}" for f in traceback.extract_tb(e.__traceback__)][-3:]
        log.error(json.dumps({"evento": "error_interno", "tipo_error": type(e).__name__, "donde": donde}))
        http, cuerpo = 500, {"error": {"codigo": "ERROR_INTERNO", "mensaje": "error interno"}}
    log.info(json.dumps({"evento": "respuesta", "ruta": f"{metodo} {recurso}", "http": http,
                         "codigo": (cuerpo.get("error") or {}).get("codigo"),
                         "ms": int((time.monotonic() - t0) * 1000)}))
    return {"statusCode": http, "headers": {"Content-Type": "application/json; charset=utf-8"},
            "body": json.dumps(cuerpo, ensure_ascii=False, default=_json)}
