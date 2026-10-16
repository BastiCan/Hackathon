"""El JSON Schema, los ejemplos y los modelos de Pydantic dicen lo mismo."""
from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator

from transcriptor.contrato import ErrorResultado, Palabra, ResultadoTranscripcion

from conftest import ESQUEMA, ejemplo, validar


def test_el_esquema_es_valido():
    Draft202012Validator.check_schema(ESQUEMA)


@pytest.mark.parametrize("nombre", ["transcribiendo", "completado", "fallido"])
def test_ejemplos_cumplen_esquema_y_modelo(nombre):
    datos = validar(ejemplo(nombre))
    assert ResultadoTranscripcion.model_validate(datos).model_dump(mode="json") == datos


def test_mismos_campos_en_esquema_y_modelos():
    assert list(ESQUEMA["properties"]) == list(ResultadoTranscripcion.model_fields)
    assert set(ESQUEMA["$defs"]["palabra"]["properties"]) == set(Palabra.model_fields)
    assert set(ESQUEMA["$defs"]["error"]["properties"]) == set(ErrorResultado.model_fields)


@pytest.mark.parametrize(
    "cambios",
    [{"estado": "transcribiendo"}, {"terminado_en": None}, {"estado": "fallido"}, {"palabras": [{"texto": "x"}]}],
)
def test_el_esquema_rechaza_combinaciones_incoherentes(cambios):
    assert list(Draft202012Validator(ESQUEMA).iter_errors(ejemplo("completado") | cambios))