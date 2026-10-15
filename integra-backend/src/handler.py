"""Lambda handler: evento -> pipeline -> respuesta.

Delgado (structure.md): valida el evento, llama a pipeline.procesar_nota y devuelve el
resultado. Los recursos pesados (rubrica, embeddings, fewshot) se cargan una vez por
contenedor (fuera del handler) y se reutilizan en invocaciones calientes.
No se escribe el texto de las notas en logs (requirements 5): solo IDs y conteos.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from core.config import config
from core.datos import crear_datos
from core.modelos import Entrada
from core.pipeline import ErrorCapturaExc, procesar_nota
from core.recursos import cargar_json
from core.retriever import Retriever
from core.rubrica import Rubrica

logging.basicConfig(level=getattr(logging, config.log_level, logging.INFO))
log = logging.getLogger("procesar_nota")

# --- Recursos cacheados por contenedor (se cargan una vez) ---
_rubrica: Rubrica | None = None
_retriever: Retriever | None = None
_fewshot: dict | None = None


def _recursos() -> tuple[Rubrica, Retriever, dict]:
    global _rubrica, _retriever, _fewshot
    if _rubrica is None:
        _rubrica = Rubrica.desde_dict(cargar_json("rubrica"))
        _retriever = Retriever.desde_dict(_rubrica, cargar_json("embeddings"))
        _fewshot = cargar_json("fewshot")
    assert _retriever is not None and _fewshot is not None
    return _rubrica, _retriever, _fewshot


def _parsear_evento(event: dict[str, Any]) -> dict[str, Any]:
    """Acepta el evento directo o envuelto en {'body': '<json>'} (estilo API Gateway)."""
    if isinstance(event, dict) and "body" in event and isinstance(event["body"], str):
        return json.loads(event["body"])
    return event


def _error(codigo: str) -> dict[str, Any]:
    return {"error": {"codigo": codigo}}


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    try:
        datos_evento = _parsear_evento(event)
        entrada = Entrada(
            texto=datos_evento.get("texto", ""),
            id_educadora=datos_evento.get("id_educadora", ""),
            sala_grupo=datos_evento.get("sala_grupo", ""),
            fecha=date.fromisoformat(datos_evento["fecha"]),
        )
    except Exception as e:  # noqa: BLE001 - evento mal formado
        log.warning("evento invalido: %s", type(e).__name__)
        return _error("ENTRADA_INVALIDA")

    rubrica, retriever, fewshot = _recursos()
    datos = crear_datos()

    try:
        resultado = procesar_nota(entrada, datos, rubrica, retriever, fewshot)
    except ErrorCapturaExc as e:
        log.info("error de captura: %s", e.codigo.value)
        return _error(e.codigo.value)
    except Exception as e:
        log.exception("error interno procesando captura (%s)", type(e).__name__)
        return {"error": {"codigo": "ERROR_INTERNO"}}

    log.info(
        "captura %s procesada: %d observaciones",
        resultado.id_captura,
        len(resultado.observaciones),
    )
    return json.loads(resultado.model_dump_json(exclude_none=True))
