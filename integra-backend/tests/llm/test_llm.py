"""Tarea 4: prueba minima con una llamada real a Bedrock (marcada -m llm).

No corre por defecto (pyproject: addopts = -m 'not llm'). Requiere credenciales y los
MODEL_ID_* en el entorno (p. ej. cargados desde .env por config.py).
"""

from __future__ import annotations

import os

import pytest

from core.llm import call_json, cargar_esquema
from core.modelos import TipoObservacion

pytestmark = pytest.mark.llm


@pytest.mark.skipif(
    not os.environ.get("MODEL_ID_SEPARAR"),
    reason="requiere MODEL_ID_SEPARAR en el entorno",
)
def test_call_json_separar_real() -> None:
    schema = cargar_esquema("separar_identificar")
    variables = {
        "fecha": "2026-10-15",
        "nomina": "N1: Pedro — apodos: Pedrito\nN2: Sofia — apodos: Sofi",
        "texto": "Pedro apilo bloques. Hoy hizo mucho frio.",
    }
    datos, meta = call_json(
        prompt_id="separar_identificar",
        variables=variables,
        schema=schema,
        model_id=os.environ["MODEL_ID_SEPARAR"],
        temperature=0,
    )

    # call_json ya garantiza que valida contra el esquema; verificamos contenido minimo.
    assert "fragmentos" in datos
    assert len(datos["fragmentos"]) >= 1
    tipos = {f["tipo"] for f in datos["fragmentos"]}
    assert tipos <= {t.value for t in (TipoObservacion.PARTICULAR, TipoObservacion.GENERAL)}

    # Metadatos sin PII.
    assert meta.model_id == os.environ["MODEL_ID_SEPARAR"]
    assert meta.prompt_id == "separar_identificar"
    assert meta.tokens_salida > 0
    assert meta.intentos >= 1
