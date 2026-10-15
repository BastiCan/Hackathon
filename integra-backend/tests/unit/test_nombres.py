"""Tarea 3.2: nombres.py normaliza y resuelve contra la nomina (casos de la demo)."""

from __future__ import annotations

from datetime import date

from core.modelos import ErrorIdentificacion, Nino
from core.nombres import normalizar, resolver


def _nino(id_nino: str, nombre: str, apodos: list[str], sala: str = "SG-A") -> Nino:
    return Nino(
        id_nino=id_nino,
        id_jardin="JAR-0001",
        sala_grupo=sala,
        nombre=nombre,
        apodos=apodos,
        fecha_nacimiento=date(2024, 1, 1),
        fecha_ingreso=date(2024, 6, 1),
    )


# Nomina de SG-A y resto del jardin (SG-B), reflejando nomina_demo.json.
NAYARA = _nino("NINO-00487", "Nayara", ["Naiara", "Naya"])
SOFIA = _nino("NINO-00372", "Sofia", ["Sofi", "la Sofi"])
PEDRO = _nino("NINO-00253", "Pedro", ["Pedrito"])
MARTINA_M = _nino("NINO-00237", "Martina M.", ["Martina", "Marti"])
MARTINA_R = _nino("NINO-00263", "Martina R.", ["Martina", "Tina"])
JOAQUIN = _nino("NINO-00216", "Joaquin", ["Joaco"], sala="SG-B")

NOMINA = [NAYARA, SOFIA, PEDRO, MARTINA_M, MARTINA_R]
RESTO_JARDIN = [JOAQUIN]


# --- normalizar ---

def test_normalizar_quita_tildes_y_colapsa_espacios() -> None:
    assert normalizar("  Joaquín   Andrés ") == "joaquin andres"


def test_normalizar_minusculas() -> None:
    assert normalizar("SOFÍA") == "sofia"


# --- resolver: casos canonicos de la demo ---

def test_resuelve_apodo_la_sofi() -> None:
    r = resolver("la Sofi", NOMINA, RESTO_JARDIN)
    assert r.resuelto
    assert r.id_nino == SOFIA.id_nino


def test_resuelve_variante_de_escritura_naiara() -> None:
    # "Naiara" es error de escritura de Nayara (apodo registrado).
    r = resolver("Naiara", NOMINA, RESTO_JARDIN)
    assert r.resuelto
    assert r.id_nino == NAYARA.id_nino


def test_dos_martina_es_ambiguo() -> None:
    r = resolver("Martina", NOMINA, RESTO_JARDIN)
    assert not r.resuelto
    assert r.error == ErrorIdentificacion.AMBIGUO
    ids = {c.id_nino for c in r.candidatos}
    assert MARTINA_M.id_nino in ids
    assert MARTINA_R.id_nino in ids


def test_joaquin_fuera_de_sala() -> None:
    r = resolver("Joaquin", NOMINA, RESTO_JARDIN)
    assert not r.resuelto
    assert r.error == ErrorIdentificacion.FUERA_DE_SALA
    assert r.candidatos[0].id_nino == JOAQUIN.id_nino


def test_catalina_no_encontrado() -> None:
    r = resolver("Catalina", NOMINA, RESTO_JARDIN)
    assert not r.resuelto
    assert r.error == ErrorIdentificacion.NO_ENCONTRADO


def test_candidatos_maximo_tres() -> None:
    r = resolver("Martina", NOMINA, RESTO_JARDIN)
    assert len(r.candidatos) <= 3


def test_resuelto_adjunta_candidatos() -> None:
    r = resolver("Pedro", NOMINA, RESTO_JARDIN)
    assert r.resuelto
    assert any(c.id_nino == PEDRO.id_nino for c in r.candidatos)
