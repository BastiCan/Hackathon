"""Tarea 3.1: edad.py reproduce exactamente la tabla de dominio.md Seccion 1."""

from __future__ import annotations

from datetime import date

import pytest

from core.edad import comparar, edad_meses, niveles_esperados
from core.modelos import ComparacionEdad
from core.rubrica import Rubrica, cargar_rubrica

# Tabla de referencia de dominio.md Seccion 1: edad_meses -> niveles_esperados.
TABLA = [
    (0, [1], False),
    (2, [1, 2], False),
    (5, [3], False),
    (12, [5, 6], False),
    (14, [6], False),
    (24, [8], False),
    (31, [9], False),
    (40, [9], True),
]


@pytest.fixture(scope="module")
def rubrica() -> Rubrica:
    return cargar_rubrica()


@pytest.mark.parametrize(("edad", "esperados", "fuera"), TABLA)
def test_niveles_esperados_tabla_dominio(
    edad: int, esperados: list[int], fuera: bool, rubrica: Rubrica
) -> None:
    niveles, fuera_de_rango = niveles_esperados(edad, rubrica)
    assert niveles == esperados
    assert fuera_de_rango == fuera


# --- edad_meses (formula del diccionario, floor, minimo 0) ---

def test_edad_meses_mismo_dia_cumple_mes_exacto() -> None:
    # Nacio el 1 de un mes; a los 3 meses justos (mismo dia) = 3.
    assert edad_meses(date(2026, 1, 1), date(2026, 4, 1)) == 3


def test_edad_meses_resta_uno_si_dia_nota_menor() -> None:
    # Aun no cumple el mes porque el dia de la nota es anterior al de nacimiento.
    assert edad_meses(date(2026, 1, 15), date(2026, 4, 10)) == 2


def test_edad_meses_nunca_negativa() -> None:
    assert edad_meses(date(2026, 10, 1), date(2026, 9, 1)) == 0


def test_edad_meses_recien_nacido() -> None:
    assert edad_meses(date(2026, 10, 1), date(2026, 10, 1)) == 0


def test_edad_meses_casos_de_la_nomina_demo() -> None:
    # Nayara (nac. 2023-06-01) a la fecha de notas_prueba (2026-10-15) = 40 meses.
    assert edad_meses(date(2023, 6, 1), date(2026, 10, 15)) == 40
    # Pedro (nac. 2024-03-01) a la misma fecha = 31 meses.
    assert edad_meses(date(2024, 3, 1), date(2026, 10, 15)) == 31
    # Vicente (nac. 2026-05-01) a la misma fecha = 5 meses.
    assert edad_meses(date(2026, 5, 1), date(2026, 10, 15)) == 5


# --- comparar ---

def test_comparar_acorde() -> None:
    assert comparar(6, [5, 6]) == ComparacionEdad.ACORDE


def test_comparar_bajo_lo_esperado() -> None:
    # Pedro: 31 meses -> esperado [9]; una conducta de nivel 7 u 8 queda por debajo.
    assert comparar(8, [9]) == ComparacionEdad.BAJO_LO_ESPERADO


def test_comparar_sobre_lo_esperado() -> None:
    assert comparar(4, [1, 2]) == ComparacionEdad.SOBRE_LO_ESPERADO


def test_comparar_fuera_de_rango_nivel_maximo_es_acorde() -> None:
    # 40 meses -> esperado [9]; un nivel 9 queda ACORDE (la bandera fuera_de_rango matiza).
    assert comparar(9, [9]) == ComparacionEdad.ACORDE


def test_comparar_fuera_de_rango_nivel_menor_es_bajo() -> None:
    assert comparar(6, [9]) == ComparacionEdad.BAJO_LO_ESPERADO
