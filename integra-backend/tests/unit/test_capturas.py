"""Tarea 8b: parseo de la ruta/evento S3 de una captura (capturas.py, sin AWS)."""

from __future__ import annotations

import pytest

from core.capturas import (
    ClaveInvalida,
    clave_archivo,
    es_id_captura,
    id_captura_de_clave,
    id_obs,
    tipo_de_clave,
)

ID_OK = "CAP-01J8Z3M4N5P6Q7R8S9T0V1W2X3"  # 26 chars base32 Crockford tras CAP-


def test_es_id_captura_valido() -> None:
    assert es_id_captura(ID_OK)


@pytest.mark.parametrize(
    "malo",
    [
        "CAP-123",                         # muy corto
        "CAP-01J8Z3M4N5P6Q7R8S9T0V1W2X",   # 25 chars
        "cap-01J8Z3M4N5P6Q7R8S9T0V1W2X3",  # minusculas en prefijo
        "01J8Z3M4N5P6Q7R8S9T0V1W2X3",      # sin CAP-
        "CAP-01I8Z3M4N5P6Q7R8S9T0V1W2X3",  # I no esta en Crockford base32
    ],
)
def test_es_id_captura_invalido(malo: str) -> None:
    assert not es_id_captura(malo)


def test_id_captura_de_clave() -> None:
    assert id_captura_de_clave(f"capturas/{ID_OK}/texto.json") == ID_OK
    assert id_captura_de_clave(f"capturas/{ID_OK}/original/foto1.jpg") == ID_OK
    assert id_captura_de_clave(f"capturas/{ID_OK}/meta.json") == ID_OK


def test_id_captura_de_clave_fuera_de_prefijo() -> None:
    with pytest.raises(ClaveInvalida):
        id_captura_de_clave(f"otracosa/{ID_OK}/texto.json")


def test_id_captura_de_clave_id_invalido() -> None:
    with pytest.raises(ClaveInvalida):
        id_captura_de_clave("capturas/NO-ULID/texto.json")


def test_tipo_de_clave() -> None:
    assert tipo_de_clave(f"capturas/{ID_OK}/meta.json") == "meta"
    assert tipo_de_clave(f"capturas/{ID_OK}/texto.json") == "texto"
    assert tipo_de_clave(f"capturas/{ID_OK}/original/foto1.jpg") == "otro"


def test_clave_archivo() -> None:
    assert clave_archivo(ID_OK, "original/foto1.jpg") == f"capturas/{ID_OK}/original/foto1.jpg"
    # Tolera barra inicial.
    assert clave_archivo(ID_OK, "/original/foto1.jpg") == f"capturas/{ID_OK}/original/foto1.jpg"


def test_id_obs_determinista() -> None:
    assert id_obs(ID_OK, 0, 0) == f"{ID_OK}-p0-0"
    assert id_obs(ID_OK, 2, 5) == f"{ID_OK}-p2-5"
    # Mismo input -> mismo id (idempotencia).
    assert id_obs(ID_OK, 1, 3) == id_obs(ID_OK, 1, 3)


# --- Modelos de captura (texto.json / meta.json) ---

def test_texto_captura_con_partes() -> None:
    from core.modelos import TextoCaptura

    tc = TextoCaptura.model_validate(
        {
            "id_captura": ID_OK,
            "fuente": "ocr",
            "partes": [{"texto": "Pedro apilo bloques", "archivo": "original/foto1.jpg"}, {"texto": "Hoy frio"}],
        }
    )
    partes = tc.partes_normalizadas()
    assert len(partes) == 2
    assert partes[0].archivo == "original/foto1.jpg"
    assert partes[1].archivo is None


def test_texto_captura_compacto_sin_partes() -> None:
    from core.modelos import TextoCaptura

    tc = TextoCaptura.model_validate({"texto": "Sofia miro por la ventana"})
    partes = tc.partes_normalizadas()
    assert len(partes) == 1
    assert partes[0].texto == "Sofia miro por la ventana"
    assert partes[0].archivo is None


def test_texto_captura_vacio() -> None:
    from core.modelos import TextoCaptura

    assert TextoCaptura().partes_normalizadas() == []


def test_meta_parsea_fecha() -> None:
    from datetime import date

    from core.modelos import Meta

    m = Meta.model_validate(
        {"id_educadora": "EDU-0001", "sala_grupo": "SG-A", "fecha_observacion": "2026-10-15", "tipo": "manual"}
    )
    assert m.fecha_observacion == date(2026, 10, 15)
