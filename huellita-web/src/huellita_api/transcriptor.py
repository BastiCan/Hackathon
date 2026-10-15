"""Cliente del servicio de transcripción (stack `transcriptor-audio`).

Hace dos cosas: manda el audio (`iniciar`) y pregunta cómo va (`consultar`).

La clave de API se pide **una sola vez, al primer uso**, con
`get_api_key(apiKey=ID_CLAVE_TRANSCRIPTOR, includeValue=True)` y queda **solo en memoria**:
nunca va a logs, ni a respuestas, ni a archivos, ni al navegador, ni a los mensajes de las
excepciones. Los logs de este módulo llevan solo ids, estados y tamaños: nunca audio, texto
transcrito ni cabeceras.

Plan B (no implementado, queda como nota): si la cuenta no deja leer la clave con
`apigateway:GET`, Lucas crea un secreto en Secrets Manager (sin mostrar su valor) y
`valor_clave_api` lo resuelve desde ahí. El resto del módulo no cambia.

Tampoco sale de aquí ninguna excepción cruda de `urllib`, `json` o `botocore`: todas se
traducen a `ErrorTranscriptor` con un código estable (los de `errores.CODIGOS_HTTP`), que
`datos/audio.py` convierte en `ErrorApi`:

| Transcriptor        | `codigo`                     | HTTP del BFF                      |
|---------------------|------------------------------|-----------------------------------|
| 413                 | `audio_demasiado_grande`     | 413 (igual)                       |
| 415                 | `formato_audio_no_soportado` | 415 (igual)                       |
| 429, 503            | `servicio_saturado`          | 503, con "intenta de nuevo"       |
| 502, 504            | `transcriptor_caido`         | 502                               |
| otro, timeout, red  | `transcriptor_caido`         | 502                               |
"""
from __future__ import annotations

import functools
import json
import logging
import urllib.error
import urllib.request

import boto3
from botocore.config import Config as ConfigBotocore

from .config import Config

TIEMPO_POST = 10
"""Segundos de espera del POST con el audio."""

TIEMPO_GET = 3
"""Segundos de espera de la consulta."""

RUTA_AUDIO = "/api/transcripciones/audio"

AJUSTES_BOTO = ConfigBotocore(connect_timeout=3, read_timeout=8, retries={"mode": "standard"})
"""Mismos tiempos límite y reintentos que usa el transcriptor en sus clientes boto3."""

_CODIGOS: dict[int, str] = {
    413: "audio_demasiado_grande",
    415: "formato_audio_no_soportado",
    429: "servicio_saturado",
    503: "servicio_saturado",
    502: "transcriptor_caido",
    504: "transcriptor_caido",
}

_LOG = logging.getLogger(__name__)


class ErrorTranscriptor(Exception):
    """Falla del transcriptor, ya traducida a un código del BFF. Nunca lleva la clave."""

    def __init__(self, codigo: str, estado: int | None = None) -> None:
        super().__init__(codigo)
        self.codigo = codigo
        self.estado = estado


@functools.cache
def valor_clave_api(cfg: Config) -> str:
    """Valor de la clave de API, pedido al primer uso y guardado solo en memoria."""
    try:
        cliente = boto3.client("apigateway", config=AJUSTES_BOTO)
        valor = cliente.get_api_key(apiKey=cfg.id_clave_transcriptor, includeValue=True)["value"]
    except Exception:
        _LOG.warning("transcriptor: no pude leer la clave de API")
        raise ErrorTranscriptor("transcriptor_caido") from None
    if not valor:
        _LOG.warning("transcriptor: la clave de API vino vacía")
        raise ErrorTranscriptor("transcriptor_caido")
    return valor


def iniciar(cfg: Config, id_captura: str, audio_base64: str) -> str:
    """Manda el audio a transcribir y devuelve el `id_trabajo` ("tr-<id_captura>")."""
    cuerpo = {"id_captura": id_captura, "audio_base64": audio_base64}
    estado, respuesta = _pedir(cfg, "POST", RUTA_AUDIO, cuerpo, TIEMPO_POST)
    if estado not in (200, 202):
        _LOG.warning("transcriptor: POST %s respondió %s", RUTA_AUDIO, estado)
        raise ErrorTranscriptor("transcriptor_caido", estado)
    id_trabajo = respuesta.get("id_trabajo")
    if not isinstance(id_trabajo, str) or not id_trabajo:
        id_trabajo = f"tr-{id_captura}"
    _LOG.info("transcriptor: %s enviado como %s (%d caracteres en base64)", id_captura, id_trabajo, len(audio_base64))
    return id_trabajo


def consultar(cfg: Config, id_trabajo: str) -> dict:
    """Pregunta cómo va un trabajo: `estado` y, si terminó bien, `texto_completo`.

    Devuelve el JSON del transcriptor tal cual. Un 404 (el trabajo ya no está) se devuelve
    como `fallido`, que para la tía es una nota que no se pudo leer.
    """
    try:
        _, respuesta = _pedir(cfg, "GET", f"/api/transcripciones/{id_trabajo}", None, TIEMPO_GET)
    except ErrorTranscriptor as fallo:
        if fallo.estado == 404:
            _LOG.info("transcriptor: %s ya no está, lo doy por fallido", id_trabajo)
            return {"estado": "fallido", "texto_completo": None}
        raise
    _LOG.info("transcriptor: %s está %s", id_trabajo, respuesta.get("estado"))
    return respuesta


def _pedir(cfg: Config, metodo: str, ruta: str, cuerpo: dict | None, tiempo: int) -> tuple[int, dict]:
    """Una llamada al transcriptor. Devuelve (estado, cuerpo) o lanza `ErrorTranscriptor`."""
    cabeceras = {"x-api-key": valor_clave_api(cfg)}
    datos = None
    if cuerpo is not None:
        cabeceras["Content-Type"] = "application/json"
        datos = json.dumps(cuerpo).encode("utf-8")
    solicitud = urllib.request.Request(cfg.url_transcriptor + ruta, data=datos, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(solicitud, timeout=tiempo) as respuesta:
            return respuesta.status, _leer_json(respuesta.read())
    except urllib.error.HTTPError as fallo:
        estado = int(fallo.code)
        _LOG.warning("transcriptor: %s %s respondió %s", metodo, ruta, estado)
        raise ErrorTranscriptor(_CODIGOS.get(estado, "transcriptor_caido"), estado) from None
    except (OSError, ValueError) as fallo:
        _LOG.warning("transcriptor: %s %s falló (%s)", metodo, ruta, type(fallo).__name__)
        raise ErrorTranscriptor("transcriptor_caido") from None


def _leer_json(crudo: bytes) -> dict:
    """El cuerpo de la respuesta como diccionario; si no se entiende, el servicio está caído."""
    try:
        cuerpo = json.loads(crudo or b"{}")
    except ValueError:
        _LOG.warning("transcriptor: respondió algo que no es JSON (%d bytes)", len(crudo))
        raise ErrorTranscriptor("transcriptor_caido") from None
    if not isinstance(cuerpo, dict):
        _LOG.warning("transcriptor: respondió un JSON que no es un objeto")
        raise ErrorTranscriptor("transcriptor_caido")
    return cuerpo
