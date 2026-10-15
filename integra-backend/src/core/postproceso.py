"""Consolidacion de N corridas de clasificacion (sin IA) — dominio.md Seccion 5.

Cada corrida devuelve (candidatas barajadas aparte) un conjunto de codigos elegidos,
cada uno con su `frase_evidencia`, un `otro_codigo_viable` y un `comentario`. Aqui se
vota entre corridas para decidir que codigos quedan, su certeza y el comentario final.
El cruce codigo -> nivel/dominio/texto lo hace rubrica.py; aqui solo se vota.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .modelos import Certeza


@dataclass(frozen=True)
class CorridaCodigo:
    """Un codigo elegido en una corrida, con su evidencia."""

    id_manifestacion: str
    frase_evidencia: str


@dataclass(frozen=True)
class Corrida:
    """Resultado de una corrida de clasificacion."""

    codigos: list[CorridaCodigo] = field(default_factory=list)
    otro_codigo_viable: str | None = None
    comentario: str = ""


@dataclass(frozen=True)
class CodigoConsolidado:
    id_manifestacion: str
    frase_evidencia: str
    certeza: Certeza
    votos: int


@dataclass(frozen=True)
class Consolidado:
    """Resultado consolidado de todas las corridas de una observacion."""

    codigos: list[CodigoConsolidado] = field(default_factory=list)
    comentario: str = ""
    alternativas: list[str] = field(default_factory=list)

    @property
    def sin_correspondencia(self) -> bool:
        return len(self.codigos) == 0


def _mayoria(n: int) -> int:
    """Cantidad minima de votos para ser mayoria estricta de n corridas."""
    return n // 2 + 1


def consolidar(corridas: list[Corrida]) -> Consolidado:
    """Consolida las corridas por codigo (dominio.md Seccion 5).

    - Un codigo queda si lo eligio la MAYORIA de las corridas.
    - certeza del codigo: alta si lo eligieron TODAS y ninguna marco otro_codigo_viable;
      media si lo eligio la mayoria, o alguna marco un otro_codigo_viable;
      baja si NINGUN codigo tuvo mayoria (se toma el mas votado).
    - Los codigos de minoria se listan como alternativas (para el comentario).
    - comentario base = comentario de una corrida que haya votado un codigo ganador.
    """
    if not corridas:
        return Consolidado()

    n = len(corridas)
    mayoria = _mayoria(n)
    hubo_otro_viable = any(c.otro_codigo_viable for c in corridas)

    # Votos y una frase de evidencia representativa por codigo.
    votos: Counter[str] = Counter()
    evidencia: dict[str, str] = {}
    for corrida in corridas:
        vistos_en_corrida: set[str] = set()
        for cod in corrida.codigos:
            if cod.id_manifestacion in vistos_en_corrida:
                continue  # un codigo cuenta como un voto por corrida
            vistos_en_corrida.add(cod.id_manifestacion)
            votos[cod.id_manifestacion] += 1
            evidencia.setdefault(cod.id_manifestacion, cod.frase_evidencia)

    if not votos:
        comentario = next((c.comentario for c in corridas if c.comentario), "")
        return Consolidado(comentario=comentario)

    con_mayoria = [cod for cod, v in votos.items() if v >= mayoria]

    if con_mayoria:
        ganadores = con_mayoria
        baja_global = False
    else:
        # Ningun codigo tuvo mayoria: se toma el mas votado (certeza baja).
        tope = max(votos.values())
        ganadores = [cod for cod, v in votos.items() if v == tope]
        baja_global = True

    # Ordenar ganadores por votos desc y luego por codigo para estabilidad.
    ganadores.sort(key=lambda cod: (-votos[cod], cod))

    codigos: list[CodigoConsolidado] = []
    for cod in ganadores:
        v = votos[cod]
        if baja_global:
            certeza = Certeza.BAJA
        elif v == n and not hubo_otro_viable:
            certeza = Certeza.ALTA
        else:
            certeza = Certeza.MEDIA
        codigos.append(
            CodigoConsolidado(
                id_manifestacion=cod,
                frase_evidencia=evidencia[cod],
                certeza=certeza,
                votos=v,
            )
        )

    ganadores_set = set(ganadores)
    alternativas = sorted(
        (cod for cod in votos if cod not in ganadores_set),
        key=lambda cod: (-votos[cod], cod),
    )

    comentario = _comentario_base(corridas, ganadores_set)

    return Consolidado(codigos=codigos, comentario=comentario, alternativas=alternativas)


def _comentario_base(corridas: list[Corrida], ganadores: set[str]) -> str:
    """El comentario de una corrida que haya votado un codigo ganador (o el primero)."""
    for corrida in corridas:
        if corrida.comentario and any(c.id_manifestacion in ganadores for c in corrida.codigos):
            return corrida.comentario
    return next((c.comentario for c in corridas if c.comentario), "")


def componer_comentario(base: str, alternativas: list[str], nota_edad: str = "") -> str:
    """Arma el comentario final: base + alternativas + nota de edad (dominio.md Seccion 5)."""
    partes: list[str] = []
    if base:
        partes.append(base.strip())
    if alternativas:
        partes.append("Otra lectura: " + ", ".join(alternativas) + ".")
    if nota_edad:
        partes.append(nota_edad.strip())
    return " ".join(partes)
