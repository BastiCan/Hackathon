"""Audio de punta a punta: valida la grabación, la manda a transcribir y pone al día
las transcripciones de una sala (SPEC-OFICIAL.md §1 y §6, CONTRATOS.md §2, tarea 7).

Este módulo es el único que traduce el transcriptor al lenguaje del BFF:
`transcriptor.ErrorTranscriptor` entra con su código ya resuelto (413, 415, 503 o 502) y
sale como `errores.ErrorApi`, que `app.py` convierte en la respuesta de la tía. La clave de
API no pasa por acá: la guarda `transcriptor.py` en memoria.

`sincronizar` es lo que corre en cada lectura de `/registros`: pregunta por los audios que
siguen en curso, guarda la transcripción que haya llegado y **nunca lanza**, así una caída
del transcriptor no voltea la pantalla de la tía.
"""
from __future__ import annotations

import base64
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from .. import errores, s3, transcriptor
from . import capturas

if TYPE_CHECKING:  # pragma: no cover - solo para los tipos
    from ..config import Config
    from ..tiempo import Reloj

#: Tope de audio decodificado que acepta el transcriptor: 4 MiB.
MAX_BYTES_AUDIO = 4194304

#: Consultas al transcriptor en paralelo por cada lectura de registros.
MAX_CONSULTAS_PARALELAS = 4

_LOG = logging.getLogger(__name__)


def decodificar(audio_base64: str) -> bytes:
    """Los bytes de la grabación.

    `base64_invalido` (422) si el base64 no se puede leer y `audio_demasiado_grande` (413)
    si pasa de `MAX_BYTES_AUDIO`.
    """
    try:
        crudo = base64.b64decode(audio_base64, validate=True)
    except Exception as falla:
        raise errores.error("base64_invalido") from falla
    if len(crudo) > MAX_BYTES_AUDIO:
        raise errores.error("audio_demasiado_grande")
    return crudo


def enviar(cfg: Config, id_captura: str, audio_base64: str) -> str:
    """Manda la grabación a transcribir y deja el `id_trabajo` en la fila.

    Si el transcriptor falla, la fila queda en `error_envio` y el código del transcriptor
    sale tal cual: 413 y 415 iguales, 429 y 503 como `servicio_saturado`, 502 y 504 como
    `transcriptor_caido`.
    """
    try:
        id_trabajo = transcriptor.iniciar(cfg, id_captura, audio_base64)
    except transcriptor.ErrorTranscriptor as falla:
        capturas.marcar_envio(cfg, id_captura, "error_envio")
        raise errores.error(falla.codigo) from falla
    capturas.marcar_envio(cfg, id_captura, "enviada", id_trabajo=id_trabajo)
    return id_trabajo


def sincronizar(cfg: Config, sala_id: str, reloj: Reloj | None = None) -> None:
    """Pregunta por los audios de la sala que siguen en curso y guarda lo que llegó.

    - `fallido` deja la nota en `error`;
    - `completado` guarda `texto_completo` y reintenta la entrega de `texto.json`;
    - `transcribiendo` no hace nada.

    El estado final de una nota transcrita lo pone Registros, no esta función: acá solo
    queda el texto. Si una consulta o una escritura falla, se anota en el log y
    `/registros` responde igual.
    """
    del reloj  # las marcas de tiempo las pone datos/capturas con la hora de Chile
    try:
        pendientes = _pendientes(cfg, sala_id)
        if pendientes:
            _consultar_y_guardar(cfg, pendientes)
    except Exception as falla:  # noqa: BLE001 - sincronizar nunca puede voltear /registros
        _LOG.warning(
            "audio: no pudimos sincronizar la sala %s (%s)", sala_id, type(falla).__name__
        )


def _pendientes(cfg: Config, sala_id: str) -> list[dict]:
    """Los audios de la sala con trabajo en el transcriptor y sin estado final."""
    return [
        fila
        for fila in capturas.leer_de_sala(cfg, sala_id)
        if _texto(fila, "formato") == "audio"
        and _texto(fila, "id_trabajo")
        and not _texto(fila, "estado_final")
    ]


def _consultar_y_guardar(cfg: Config, pendientes: list[dict]) -> None:
    """Consulta de a `MAX_CONSULTAS_PARALELAS`. Una fila que falla no detiene a las demás."""
    with ThreadPoolExecutor(max_workers=MAX_CONSULTAS_PARALELAS) as grupo:
        consultas = {
            grupo.submit(transcriptor.consultar, cfg, _texto(fila, "id_trabajo")): fila
            for fila in pendientes
        }
        for consulta in as_completed(consultas):
            fila = consultas[consulta]
            try:
                _aplicar(cfg, fila, consulta.result())
            except Exception as falla:  # noqa: BLE001 - una transcripción que falla no rompe la lectura
                # Solo el id y el tipo de la falla, como en `transcriptor.py`: el mensaje de
                # una excepción del transcriptor podría llevar cabeceras, y la clave de API
                # no entra a los logs por ninguna vía.
                _LOG.warning(
                    "audio: no pudimos poner al día la transcripción de %s (%s)",
                    _texto(fila, "id_captura"),
                    type(falla).__name__,
                )


def _aplicar(cfg: Config, fila: dict, respuesta: object) -> None:
    """Guarda lo que respondió el transcriptor para una captura."""
    if not isinstance(respuesta, dict):
        return
    id_captura = _texto(fila, "id_captura")
    estado = respuesta.get("estado")
    if estado == "fallido":
        capturas.marcar_final(cfg, id_captura, "error")
        return
    texto = respuesta.get("texto_completo")
    if estado != "completado" or not isinstance(texto, str) or not texto:
        return
    capturas.guardar_texto(cfg, id_captura, texto)
    if _bandera(fila, "texto_entregado"):
        return
    s3.subir_json(cfg, s3.clave_texto(id_captura), s3.cuerpo_texto(id_captura, texto, "audio"))
    capturas.marcar_envio(cfg, id_captura, "enviada", texto_entregado=True)


def _texto(fila: dict, clave: str) -> str:
    """Un atributo `S` de la fila cruda ("" si falta)."""
    valor = fila.get(clave, {}).get("S", "")
    return valor if isinstance(valor, str) else ""


def _bandera(fila: dict, clave: str) -> bool:
    """Un atributo `BOOL` de la fila cruda (`False` si falta)."""
    return fila.get(clave, {}).get("BOOL") is True
