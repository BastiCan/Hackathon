"""Carga de la rubrica y cruce codigo -> nivel, dominio, texto_observable (sin IA).

El LLM solo elige `id_manifestacion`; aqui se resuelve el resto por diccionario
(dominio.md Seccion 2, D8). La cantidad de niveles y de codigos NO se asume: todo
sale de rubrica.json (tech.md).

Tambien vive aqui el reemplazo de las claves `x-enum-from` / `x-range-from` de los
esquemas por `enum` / `minimum`-`maximum`, que usan tanto el test de la tarea 2
como `llm.py` (tarea 4): asi la fuente de los enums es siempre la rubrica cargada.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import RUBRICA_LOCAL


@dataclass(frozen=True)
class Nivel:
    nivel: int
    nombre_nivel: str
    edad_min_meses: int
    edad_max_meses: int
    descripcion: str


@dataclass(frozen=True)
class Cruce:
    """Datos de un codigo de manifestacion resueltos desde la rubrica."""

    id_manifestacion: str
    nivel: int
    dominio: str
    texto_observable: str


class Rubrica:
    """Vista de solo lectura sobre rubrica.json."""

    def __init__(self, datos: dict[str, Any]) -> None:
        self._datos = datos
        self.version: str = datos.get("version", "")
        self.dominios: list[str] = list(datos["dominios"])
        self.niveles: list[Nivel] = [
            Nivel(
                nivel=n["nivel"],
                nombre_nivel=n["nombre_nivel"],
                edad_min_meses=n["edad_min_meses"],
                edad_max_meses=n["edad_max_meses"],
                descripcion=n["descripcion"],
            )
            for n in datos["niveles"]
        ]
        self._manifestaciones: dict[str, dict[str, Any]] = datos["manifestaciones"]

    # --- Carga ---

    @classmethod
    def desde_dict(cls, datos: dict[str, Any]) -> Rubrica:
        return cls(datos)

    @classmethod
    def desde_archivo(cls, ruta: str | Path = RUBRICA_LOCAL) -> Rubrica:
        with Path(ruta).open(encoding="utf-8") as f:
            return cls(json.load(f))

    # --- Consultas ---

    @property
    def codigos(self) -> list[str]:
        """Los IDs de manifestacion (en el orden de rubrica.json)."""
        return list(self._manifestaciones.keys())

    @property
    def numeros_de_nivel(self) -> list[int]:
        return [n.nivel for n in self.niveles]

    def existe(self, id_manifestacion: str) -> bool:
        return id_manifestacion in self._manifestaciones

    def nivel_de(self, numero: int) -> Nivel:
        for n in self.niveles:
            if n.nivel == numero:
                return n
        raise KeyError(f"nivel desconocido: {numero}")

    def cruzar(self, id_manifestacion: str) -> Cruce:
        """Codigo -> nivel, dominio, texto_observable. Lanza KeyError si no existe."""
        m = self._manifestaciones[id_manifestacion]
        return Cruce(
            id_manifestacion=id_manifestacion,
            nivel=m["nivel"],
            dominio=m["dominio"],
            texto_observable=m["texto_observable"],
        )


# --- Reemplazo de x-enum-from / x-range-from en los esquemas ---

def _valores_para(ref: str, rubrica: Rubrica) -> list[Any]:
    """Devuelve la lista de valores que corresponde a una referencia `x-enum-from`.

    Hoy solo se usa `rubrica.manifestaciones` (los 90 codigos). Se deja extensible
    por si un esquema futuro referencia dominios o niveles.
    """
    if ref == "rubrica.manifestaciones":
        return rubrica.codigos
    if ref == "rubrica.dominios":
        return list(rubrica.dominios)
    if ref == "rubrica.niveles":
        return rubrica.numeros_de_nivel
    raise ValueError(f"referencia x-enum-from/x-range-from desconocida: {ref}")


def resolver_esquema(esquema: dict[str, Any], rubrica: Rubrica) -> dict[str, Any]:
    """Devuelve una copia del esquema con las claves `x-*-from` ya resueltas.

    - `x-enum-from`: se reemplaza por `enum` con la lista tomada de la rubrica.
    - `x-range-from`: se reemplaza por `minimum`/`maximum` (min y max de la lista).
    Recorre todo el arbol del esquema (dicts y lists).
    """
    copia = copy.deepcopy(esquema)
    _resolver_en_sitio(copia, rubrica)
    return copia


def _admite_null(tipo: Any) -> bool:
    """True si el `type` del nodo permite null (string u lista que incluye 'null')."""
    if tipo == "null":
        return True
    if isinstance(tipo, list):
        return "null" in tipo
    return False


def _resolver_en_sitio(nodo: Any, rubrica: Rubrica) -> None:
    if isinstance(nodo, dict):
        if "x-enum-from" in nodo:
            ref = nodo.pop("x-enum-from")
            valores = list(_valores_para(ref, rubrica))
            # Si el type del campo admite null (p. ej. otro_codigo_viable), el enum
            # debe incluir None para permitir el valor nulo (igual que en llm.py).
            if _admite_null(nodo.get("type")):
                valores.append(None)
            nodo["enum"] = valores
        if "x-range-from" in nodo:
            ref = nodo.pop("x-range-from")
            valores = _valores_para(ref, rubrica)
            nodo["minimum"] = min(valores)
            nodo["maximum"] = max(valores)
        for valor in nodo.values():
            _resolver_en_sitio(valor, rubrica)
    elif isinstance(nodo, list):
        for item in nodo:
            _resolver_en_sitio(item, rubrica)


# Instancia perezosa para uso directo en local.
_rubrica_cache: Rubrica | None = None


def cargar_rubrica(ruta: str | Path = RUBRICA_LOCAL) -> Rubrica:
    """Carga (y cachea) la rubrica desde el archivo local."""
    global _rubrica_cache
    if _rubrica_cache is None:
        _rubrica_cache = Rubrica.desde_archivo(ruta)
    return _rubrica_cache
