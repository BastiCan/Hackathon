"""Foto de post-its de punta a punta: valida la imagen e invoca el OCR.

Este módulo es el único que traduce el OCR al lenguaje del BFF: `ocr.ErrorOcr`
entra con su código ya resuelto (`foto_invalida`, `foto_demasiado_grande`,
`formato_foto_no_soportado`, `ocr_sin_lectura`, `ocr_caido`) y sale como
`errores.ErrorApi`, que `app.py` convierte en la respuesta de la tía. Molde:
`datos/audio.py` (marca `error_envio` ante fallo, no cae la captura ante timeout).

`enviar` NO escribe `texto.json`: eso lo hace la Lambda `postits-ocr`, que al dejar
`meta.json`/`texto.json` en S3 dispara ProcesarNota. Si el OCR no responde a tiempo
(`OcrEnProceso`), la fila queda `enviada` y la lectura termina igual en caliente.
"""
from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

from .. import errores, ocr
from . import capturas

if TYPE_CHECKING:  # pragma: no cover - solo para los tipos
    from ..config import Config

#: Tope de imagen decodificada: ~5.5 MiB, para quedar bajo el límite de 6 MB de
#: payload de Lambda incluso con el resto del evento.
MAX_BYTES_FOTO = 5767168

#: Magic bytes por formato aceptado.
_JPEG = b"\xff\xd8\xff"
_PNG = b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"
#: Marcas `ftyp` de HEIC/HEIF (fotos de iPhone), que postits-ocr rechaza.
_FTYP_HEIF = (b"heic", b"heix", b"heif", b"hevc", b"mif1", b"msf1")

_LOG = logging.getLogger(__name__)


def decodificar(foto_base64: str | None) -> tuple[bytes, str]:
    """Los bytes de la foto y su `content_type` (`image/jpeg` o `image/png`).

    `foto_invalida` (422) si el base64 no se puede leer o el formato no se reconoce;
    `foto_demasiado_grande` (413) si pasa de `MAX_BYTES_FOTO`;
    `formato_foto_no_soportado` (415) si es HEIC/HEIF.
    """
    if not foto_base64:
        raise errores.error("foto_invalida")
    try:
        crudo = base64.b64decode(foto_base64, validate=True)
    except Exception as falla:
        raise errores.error("foto_invalida") from falla
    if not crudo:
        raise errores.error("foto_invalida")
    if len(crudo) > MAX_BYTES_FOTO:
        raise errores.error("foto_demasiado_grande")
    return crudo, _tipo(crudo)


def _tipo(crudo: bytes) -> str:
    """`content_type` por los magic bytes; traduce HEIC/HEIF y lo demás a errores."""
    if crudo.startswith(_JPEG):
        return "image/jpeg"
    if crudo.startswith(_PNG):
        return "image/png"
    if len(crudo) >= 12 and crudo[4:8] == b"ftyp" and crudo[8:12] in _FTYP_HEIF:
        raise errores.error("formato_foto_no_soportado")
    raise errores.error("foto_invalida")


def enviar(cfg: Config, id_captura: str, id_educadora: str, sala_grupo: str, fecha: str) -> None:
    """Invoca el OCR para una foto ya subida a S3.

    Si el OCR falla (`ErrorOcr`), la fila queda en `error_envio` y el código sale
    tal cual (`formato_foto_no_soportado`, `foto_demasiado_grande`, `foto_invalida`,
    `ocr_sin_lectura` o `ocr_caido`). Si no responde a tiempo (`OcrEnProceso`), la
    fila queda `enviada` y no se lanza: ProcesarNota terminará la lectura.
    """
    try:
        ocr.invocar(cfg, id_captura, id_educadora, sala_grupo, fecha)
    except ocr.OcrEnProceso:
        _LOG.info("foto: %s sigue en lectura, la dejo en proceso", id_captura)
        capturas.marcar_envio(cfg, id_captura, "enviada")
        return
    except ocr.ErrorOcr as falla:
        capturas.marcar_envio(cfg, id_captura, "error_envio")
        raise errores.error(falla.codigo) from falla
    capturas.marcar_envio(cfg, id_captura, "enviada")
