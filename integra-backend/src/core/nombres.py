"""Normalizacion y resolucion de nombres contra la nomina (sin IA).

El LLM propone un nombre tal como aparece en la nota; aqui se confirma contra la
nomina de la sala con similitud difusa (rapidfuzz). Reglas (design.md Seccion 3):
- Se normaliza nombre + apodos (minusculas, sin tildes/n~, espacios colapsados).
- Match si el mejor puntaje >= UMBRAL (88).
- AMBIGUO si dos candidatos >= UMBRAL o la diferencia entre los dos mejores < MARGEN (5).
- Si no calza en la sala pero si en el resto del jardin -> FUERA_DE_SALA.
- Si no calza con nadie -> NO_ENCONTRADO.
Siempre se devuelven hasta 3 candidatos (top por puntaje), con su id y nombre.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from rapidfuzz import fuzz

from .modelos import Candidato, ErrorIdentificacion, Nino

UMBRAL = 88
MARGEN = 5
TOP_CANDIDATOS = 3


def normalizar(texto: str) -> str:
    """Minusculas, sin tildes ni n~, espacios colapsados."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return " ".join(sin_tildes.lower().split())


def _puntaje_contra_nino(consulta_norm: str, nino: Nino) -> int:
    """Mejor WRatio del nombre/apodos del nino contra la consulta normalizada."""
    variantes = [nino.nombre, *nino.apodos]
    mejor = 0.0
    for v in variantes:
        mejor = max(mejor, fuzz.WRatio(consulta_norm, normalizar(v)))
    return round(mejor)


def _candidatos_ordenados(consulta_norm: str, ninos: list[Nino]) -> list[tuple[Nino, int]]:
    puntuados = [(n, _puntaje_contra_nino(consulta_norm, n)) for n in ninos]
    puntuados.sort(key=lambda t: t[1], reverse=True)
    return puntuados


def _a_candidatos(puntuados: list[tuple[Nino, int]]) -> list[Candidato]:
    return [
        Candidato(id_nino=n.id_nino, nombre=n.nombre, score=p)
        for n, p in puntuados[:TOP_CANDIDATOS]
    ]


@dataclass(frozen=True)
class Resolucion:
    """Resultado de resolver un nombre contra la nomina."""

    id_nino: str | None = None
    error: ErrorIdentificacion | None = None
    candidatos: list[Candidato] = field(default_factory=list)

    @property
    def resuelto(self) -> bool:
        return self.id_nino is not None


def resolver(nombre_en_texto: str, nomina: list[Nino], resto_jardin: list[Nino]) -> Resolucion:
    """Resuelve un nombre contra la nomina de la sala; si no, mira el resto del jardin.

    - Un unico candidato >= UMBRAL (y sin otro empatado dentro de MARGEN) -> resuelto.
    - Dos o mas >= UMBRAL, o diferencia entre los dos mejores < MARGEN -> AMBIGUO.
    - Sin match en la sala pero si en el resto del jardin -> FUERA_DE_SALA.
    - Sin match en ningun lado -> NO_ENCONTRADO.
    """
    consulta = normalizar(nombre_en_texto)
    en_sala = _candidatos_ordenados(consulta, nomina)

    sobre_umbral = [t for t in en_sala if t[1] >= UMBRAL]
    if sobre_umbral:
        mejor_nino, mejor_score = en_sala[0]
        segundo_score = en_sala[1][1] if len(en_sala) > 1 else -1
        ambiguo = len(sobre_umbral) >= 2 or (mejor_score - segundo_score) < MARGEN
        if ambiguo:
            return Resolucion(error=ErrorIdentificacion.AMBIGUO, candidatos=_a_candidatos(en_sala))
        return Resolucion(id_nino=mejor_nino.id_nino, candidatos=_a_candidatos(en_sala))

    # No calza en la sala: revisar el resto del jardin (FUERA_DE_SALA).
    en_jardin = _candidatos_ordenados(consulta, resto_jardin)
    if en_jardin and en_jardin[0][1] >= UMBRAL:
        return Resolucion(
            error=ErrorIdentificacion.FUERA_DE_SALA,
            candidatos=_a_candidatos(en_jardin),
        )

    # Nadie supera el umbral: NO_ENCONTRADO con los mejores candidatos de la sala.
    return Resolucion(error=ErrorIdentificacion.NO_ENCONTRADO, candidatos=_a_candidatos(en_sala))
