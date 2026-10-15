"""Edad en meses y niveles esperados (solo codigo, despues de evaluar).

El LLM nunca ve la edad (dominio.md Seccion 1). Aqui se calcula a partir de la fecha
de nacimiento y la fecha de la nota, y se compara con los rangos de `ruta_niveles`
(que vienen en rubrica.json). La cantidad de niveles no se asume: sale de la rubrica.
"""

from __future__ import annotations

from datetime import date

from .modelos import ComparacionEdad
from .rubrica import Rubrica


def edad_meses(fecha_nac: date, fecha_nota: date) -> int:
    """Meses completos entre nacimiento y la nota (floor), minimo 0.

    Formula del diccionario de datos:
        12*(a2-a1) + (m2-m1) - 1[d2 < d1]
    donde (a1, m1, d1) es el nacimiento y (a2, m2, d2) la fecha de la nota.
    """
    meses = 12 * (fecha_nota.year - fecha_nac.year) + (fecha_nota.month - fecha_nac.month)
    if fecha_nota.day < fecha_nac.day:
        meses -= 1
    return max(meses, 0)


def niveles_esperados(edad: int, rubrica: Rubrica) -> tuple[list[int], bool]:
    """Niveles cuyo rango [edad_min, edad_max] contiene la edad (bordes inclusivos).

    - En un borde hay dos niveles (p. ej. 12 meses cae en [9,12] y [12,18] -> [5, 6]).
    - Si la edad supera el maximo de la rubrica -> [ultimo nivel] con fuera_de_rango=True.
    Devuelve (niveles ordenados, fuera_de_rango_rubrica).
    """
    edad_max_rubrica = max(n.edad_max_meses for n in rubrica.niveles)
    if edad > edad_max_rubrica:
        ultimo = max(n.nivel for n in rubrica.niveles)
        return [ultimo], True

    niveles = sorted(
        n.nivel
        for n in rubrica.niveles
        if n.edad_min_meses <= edad <= n.edad_max_meses
    )
    return niveles, False


def comparar(nivel: int, esperados: list[int]) -> ComparacionEdad:
    """Compara el nivel sugerido con el rango de niveles esperados para la edad.

    BAJO_LO_ESPERADO si nivel < min; ACORDE si esta dentro; SOBRE_LO_ESPERADO si > max.
    Cuando la edad esta fuera de rango, `esperados` es [ultimo nivel]: un nivel igual
    al ultimo queda ACORDE (la bandera fuera_de_rango_rubrica lo matiza) y uno menor,
    BAJO_LO_ESPERADO (dominio.md Seccion 1).
    """
    if not esperados:
        return ComparacionEdad.ACORDE
    minimo = min(esperados)
    maximo = max(esperados)
    if nivel < minimo:
        return ComparacionEdad.BAJO_LO_ESPERADO
    if nivel > maximo:
        return ComparacionEdad.SOBRE_LO_ESPERADO
    return ComparacionEdad.ACORDE
