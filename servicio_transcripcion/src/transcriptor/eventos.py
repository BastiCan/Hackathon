"""Handler de EventBridge: cuando un trabajo de Transcribe termina, guarda el JSON final en S3."""
from __future__ import annotations

import logging
from typing import Any

from .servicio import obtener_servicio

logger = logging.getLogger("transcriptor")


def handler(evento: dict[str, Any], _contexto: Any = None) -> dict[str, Any]:
    nombre = (evento.get("detail") or {}).get("TranscriptionJobName")
    if not isinstance(nombre, str) or not nombre:
        logger.warning("evento_sin_trabajo")
        return {"procesado": False}
    # consultar() guarda el resultado y entrega texto.json si el trabajo terminó. Si falta meta.json
    # o algo falla, el error se relanza para que Lambda reintente (2 veces, en unos 3 minutos).
    resultado = obtener_servicio().consultar(nombre, exigir_entrega=True)
    if resultado is None:
        logger.info("evento_ignorado", extra={"id_trabajo": nombre})
        return {"procesado": False, "id_trabajo": nombre}
    return {"procesado": resultado.estado != "transcribiendo", "id_trabajo": nombre, "estado": resultado.estado}