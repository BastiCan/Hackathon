"""Tarea 8c: serializacion y claves derivadas de datos_aws (sin AWS).

Solo se prueban las funciones puras (sala_key, orden, timestamps, serializacion de
items). La parte que habla con DynamoDB (DatosDynamo) no se instancia aqui.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

from core.datos_aws import (
    _a_item_dynamo,
    _observacion_a_item,
    ahora_iso,
    clave_orden,
    sala_key,
)
from core.modelos import Observacion, TipoObservacion

ID_CAP = "CAP-01J8Z3M4N5P6Q7R8S9T0V1W2X3"


def test_sala_key() -> None:
    assert sala_key("JAR-0001", "SG-A") == "JAR-0001#SG-A"


def test_clave_orden() -> None:
    assert clave_orden("2026-10-15", "2026-10-15T12:00:00-03:00") == "2026-10-15#2026-10-15T12:00:00-03:00"


def test_ahora_iso_tiene_zona_chile() -> None:
    iso = ahora_iso()
    # ISO 8601 con zona -03:00 y segundos (sin microsegundos).
    assert iso.endswith("-03:00")
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-03:00$", iso)


def test_a_item_dynamo_tipos() -> None:
    item = _a_item_dynamo(
        {
            "f": 1.5,
            "n": 3,
            "b": True,
            "fecha": date(2026, 10, 15),
            "nulo": None,
            "lista": [1.0, {"x": 2.5, "y": None}],
        }
    )
    assert item["f"] == Decimal("1.5")
    assert item["n"] == 3
    assert item["b"] is True
    assert item["fecha"] == "2026-10-15"
    assert "nulo" not in item  # los None se omiten
    assert item["lista"][0] == Decimal("1.0")
    assert item["lista"][1] == {"x": Decimal("2.5")}  # None interno omitido


def _cabecera() -> dict:
    return {
        "fecha": "2026-10-15",
        "id_educadora": "EDU-0001",
        "id_jardin": "JAR-0001",
        "sala_grupo": "SG-A",
    }


def test_observacion_a_item_claves_derivadas() -> None:
    obs = Observacion(
        id_obs=f"{ID_CAP}-p0-0",
        tipo=TipoObservacion.PARTICULAR,
        texto_literal="Pedro apilo tres bloques",
        id_nino="NIN-0001",
        nivel=4,
        archivo_s3=f"capturas/{ID_CAP}/original/foto1.jpg",
    )
    item = _observacion_a_item(
        obs, ID_CAP, _cabecera(), origen="app", creado_en="2026-10-15T12:00:00-03:00"
    )
    assert item["id_captura"] == ID_CAP
    assert item["id_obs"] == f"{ID_CAP}-p0-0"
    assert item["sala_key"] == "JAR-0001#SG-A"
    assert item["orden"] == "2026-10-15#2026-10-15T12:00:00-03:00"
    assert item["origen"] == "app"
    assert item["creado_en"] == "2026-10-15T12:00:00-03:00"
    assert item["id_nino"] == "NIN-0001"
    assert item["nivel"] == 4
    assert item["archivo_s3"] == f"capturas/{ID_CAP}/original/foto1.jpg"
    # Campos de cabecera presentes.
    assert item["id_jardin"] == "JAR-0001"
    assert item["sala_grupo"] == "SG-A"


def test_observacion_a_item_omite_none() -> None:
    obs = Observacion(
        id_obs=f"{ID_CAP}-p0-1",
        tipo=TipoObservacion.GENERAL,
        texto_literal="Hoy hizo frio",
    )
    item = _observacion_a_item(obs, ID_CAP, _cabecera(), creado_en="2026-10-15T12:00:00-03:00")
    # Sin nivel ni id_nino: no deben aparecer como null.
    assert "id_nino" not in item
    assert "nivel" not in item
    assert "archivo_s3" not in item
    assert item["origen"] == "app"
