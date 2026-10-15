"""Identificación demo de las tías: la cabecera `X-Usuaria-Id` contra `usuarias_demo.json`.

No hay contraseñas ni tokens: la demo confía en el id que manda la app y solo comprueba que
exista y que la sala pedida sea suya (alcance por sala).
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

from huellita_api import errores
from huellita_api.config import Config
from huellita_api.modelos import Usuaria

#: Cabecera con el id de la tía que está usando la app.
CABECERA_USUARIA = "X-Usuaria-Id"

_ARCHIVO_USUARIAS = Path(__file__).parent / "datos" / "usuarias_demo.json"


@functools.cache
def usuarias() -> list[Usuaria]:
    """Las tías de la demo, en el orden del archivo (se lee una sola vez)."""
    contenido = json.loads(_ARCHIVO_USUARIAS.read_text(encoding="utf-8"))
    return [Usuaria(**fila) for fila in contenido["usuarias"]]


def _buscar(id_usuaria: str) -> Usuaria | None:
    for usuaria in usuarias():
        if usuaria.id == id_usuaria:
            return usuaria
    return None


def existe(id_usuaria: str) -> bool:
    """True si el id está en `usuarias_demo.json`."""
    return _buscar(id_usuaria) is not None


def usuaria_o_error(id_usuaria: str | None) -> Usuaria:
    """La tía de la cabecera. Sin cabecera -> `sin_acceso`; id desconocido -> `autora_desconocida`."""
    if not id_usuaria:
        raise errores.error("sin_acceso")
    usuaria = _buscar(id_usuaria)
    if usuaria is None:
        raise errores.error("autora_desconocida")
    return usuaria


def exigir_sala(cfg: Config, usuaria: Usuaria, sala_id: str) -> None:
    """Primero mira si la sala es de la demo y después si es de la tía."""
    if sala_id not in cfg.salas:
        raise errores.error("sala_desconocida")
    if sala_id not in usuaria.salaIds:
        raise errores.error("sin_acceso")
