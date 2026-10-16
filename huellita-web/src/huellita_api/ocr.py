"""Cliente de la Lambda de OCR de post-its (stack `postits-ocr`).

Hace una sola cosa: invocar la función `postits-ocr` de forma síncrona
(`InvocationType="RequestResponse"`) con el `id_captura` de una foto ya subida a
S3, y devolver su respuesta. La foto NO viaja en el evento: tiene que estar antes
en `capturas/{id}/original/foto.jpg` (eso lo hace la ruta, no este módulo).

Igual que `transcriptor.py`, ninguna excepción cruda de `boto3`/`botocore`/`json`
sale de aquí: los errores que la Lambda devuelve en `{"error": {"codigo"}}` se
traducen a un código estable del BFF (`errores.CODIGOS_HTTP`) y salen como
`ErrorOcr`, que `datos/foto.py` convierte en `ErrorApi`:

| postits-ocr                                                  | `codigo` del BFF            |
|--------------------------------------------------------------|-----------------------------|
| FORMATO_NO_SOPORTADO                                         | formato_foto_no_soportado   |
| IMAGEN_DEMASIADO_GRANDE                                      | foto_demasiado_grande       |
| IMAGEN_NO_ENCONTRADA, IMAGEN_NO_DECODIFICABLE, PETICION_INVALIDA | foto_invalida           |
| LECTURA_NO_DISPONIBLE                                        | ocr_sin_lectura             |
| ERROR_ALMACENAMIENTO, CONFIGURACION, ERROR_INTERNO, desconocido | ocr_caido                |

ROBUSTEZ: la Lambda tarda típico ~3-4 s pero su timeout es 60 s; si la invocación
no responde a tiempo (timeout de red) NO se traduce a error: se levanta
`OcrEnProceso`, para que la ruta deje la captura `procesando` y ProcesarNota
termine igual cuando la Lambda escriba `texto.json`. Los logs llevan solo ids y
códigos: nunca el payload de la imagen.
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config as ConfigBotocore
from botocore.exceptions import ConnectTimeoutError, ReadTimeoutError

if TYPE_CHECKING:  # pragma: no cover - solo para los tipos
    from .config import Config

#: read_timeout > 60 s (el timeout de la Lambda), sin reintentos: una invocación lenta
#: no se multiplica y, si se pasa, la tratamos como "en proceso".
AJUSTES_BOTO = ConfigBotocore(
    connect_timeout=5, read_timeout=70, retries={"max_attempts": 1}
)

MODO = "opencv"

_CODIGOS: dict[str, str] = {
    "FORMATO_NO_SOPORTADO": "formato_foto_no_soportado",
    "IMAGEN_DEMASIADO_GRANDE": "foto_demasiado_grande",
    "IMAGEN_NO_ENCONTRADA": "foto_invalida",
    "IMAGEN_NO_DECODIFICABLE": "foto_invalida",
    "PETICION_INVALIDA": "foto_invalida",
    "LECTURA_NO_DISPONIBLE": "ocr_sin_lectura",
    "ERROR_ALMACENAMIENTO": "ocr_caido",
    "CONFIGURACION": "ocr_caido",
    "ERROR_INTERNO": "ocr_caido",
}

_LOG = logging.getLogger(__name__)


class ErrorOcr(Exception):
    """Falla del OCR, ya traducida a un código del BFF. Nunca lleva el payload."""

    def __init__(self, codigo: str) -> None:
        super().__init__(codigo)
        self.codigo = codigo


class OcrEnProceso(Exception):
    """El OCR no respondió a tiempo. No es un error: la lectura sigue en caliente
    y ProcesarNota la terminará cuando la Lambda escriba `texto.json`."""


def _cliente():
    """Cliente de Lambda, con los tiempos límite de este módulo."""
    return boto3.client("lambda", config=AJUSTES_BOTO)


def invocar(cfg: Config, id_captura: str, id_educadora: str, sala_grupo: str, fecha: str) -> dict:
    """Invoca `postits-ocr` sincrónicamente y devuelve su respuesta como dict.

    Levanta `ErrorOcr` (con el código del BFF ya resuelto) si la Lambda devuelve
    `{"error": {"codigo"}}` o responde algo ilegible; levanta `OcrEnProceso` si la
    invocación no responde a tiempo (timeout de red).
    """
    evento = {
        "id_captura": id_captura,
        "id_educadora": id_educadora,
        "sala_grupo": sala_grupo,
        "fecha_observacion": fecha,
        "modo": MODO,
        "escribir_texto": True,
        "incluir_urls": False,
    }
    try:
        salida = _cliente().invoke(
            FunctionName=cfg.funcion_ocr,
            InvocationType="RequestResponse",
            Payload=json.dumps(evento).encode("utf-8"),
        )
    except (ReadTimeoutError, ConnectTimeoutError):
        _LOG.info("ocr: %s no respondió a tiempo, lo dejo en proceso", id_captura)
        raise OcrEnProceso from None
    except Exception as falla:
        if _es_timeout(falla):
            _LOG.info("ocr: %s no respondió a tiempo, lo dejo en proceso", id_captura)
            raise OcrEnProceso from None
        _LOG.warning("ocr: no pude invocar %s (%s)", id_captura, type(falla).__name__)
        raise ErrorOcr("ocr_caido") from None

    respuesta = _leer_payload(salida)
    if salida.get("FunctionError"):
        _LOG.warning("ocr: %s respondió FunctionError", id_captura)
        raise ErrorOcr("ocr_caido")
    error = respuesta.get("error")
    if isinstance(error, dict):
        crudo = error.get("codigo", "")
        codigo = _CODIGOS.get(crudo if isinstance(crudo, str) else "", "ocr_caido")
        _LOG.warning("ocr: %s respondió %s -> %s", id_captura, crudo, codigo)
        raise ErrorOcr(codigo)
    _LOG.info("ocr: %s leído con %s post-its", id_captura, respuesta.get("n_postits"))
    return respuesta


def _leer_payload(salida: dict) -> dict:
    """El `Payload` de la invocación como dict; si no se entiende, el OCR está caído."""
    cuerpo = salida.get("Payload")
    crudo = cuerpo.read() if hasattr(cuerpo, "read") else cuerpo
    try:
        datos = json.loads(crudo or b"{}")
    except ValueError:
        _LOG.warning("ocr: respondió algo que no es JSON")
        raise ErrorOcr("ocr_caido") from None
    if not isinstance(datos, dict):
        _LOG.warning("ocr: respondió un JSON que no es un objeto")
        raise ErrorOcr("ocr_caido")
    return datos


def _es_timeout(falla: BaseException) -> bool:
    """Reconoce un timeout de red aunque llegue envuelto en otra excepción de botocore."""
    nombre = type(falla).__name__.lower()
    return "timeout" in nombre
