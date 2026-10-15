"""Parseo de la ruta/evento S3 de una captura (sin AWS; puro y testeable).

Layout en el bucket de capturas:
    capturas/{id_captura}/meta.json
    capturas/{id_captura}/original/<archivo>
    capturas/{id_captura}/texto.json

`id_captura` tiene formato CAP-<ULID> (ULID = 26 caracteres Crockford base32).
"""

from __future__ import annotations

import re

PREFIJO = "capturas/"
# ULID: 26 chars del alfabeto Crockford base32 (sin I, L, O, U).
_ID_CAPTURA_RE = re.compile(r"^CAP-[0-9A-HJKMNP-TV-Z]{26}$")


class ClaveInvalida(ValueError):
    """La clave S3 no corresponde a una captura valida."""


def es_id_captura(valor: str) -> bool:
    """True si `valor` tiene el formato CAP-<ULID>."""
    return bool(_ID_CAPTURA_RE.match(valor))


def id_captura_de_clave(key: str) -> str:
    """De 'capturas/CAP-.../texto.json' extrae 'CAP-...'. Lanza ClaveInvalida si no calza."""
    if not key.startswith(PREFIJO):
        raise ClaveInvalida(f"clave fuera del prefijo {PREFIJO}: {key}")
    resto = key[len(PREFIJO):]
    id_captura = resto.split("/", 1)[0]
    if not es_id_captura(id_captura):
        raise ClaveInvalida(f"id_captura invalido en la clave: {id_captura}")
    return id_captura


def tipo_de_clave(key: str) -> str:
    """Clasifica el objeto por su sufijo: 'meta' | 'texto' | 'otro'."""
    if key.endswith("/meta.json"):
        return "meta"
    if key.endswith("/texto.json"):
        return "texto"
    return "otro"


def clave_archivo(id_captura: str, archivo: str) -> str:
    """Clave S3 completa de un archivo de la parte (relativo a la carpeta de la captura).

    'original/foto1.jpg' -> 'capturas/{id_captura}/original/foto1.jpg'.
    """
    relativo = archivo.lstrip("/")
    return f"{PREFIJO}{id_captura}/{relativo}"


def id_obs(id_captura: str, n_parte: int, n_obs: int) -> str:
    """ID determinista de observacion: {id_captura}-p{n_parte}-{n_obs}.

    Deterministico para que un reintento de S3 sobrescriba y no duplique.
    """
    return f"{id_captura}-p{n_parte}-{n_obs}"
