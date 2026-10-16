"""Identificador de captura `CAP-<ULID>` (CONTRATOS.md §6).

128 bits: 48 de tiempo en milisegundos en la parte alta y 80 aleatorios de
`secrets` en la parte baja, escritos en base32 de Crockford. Se arma a mano
porque no hay paquete `ulid` entre las dependencias.
"""
from __future__ import annotations

import re
import secrets
import time

ALFABETO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
RE_ID_CAPTURA = re.compile(r"^CAP-[0-9A-HJKMNP-TV-Z]{26}$")

PREFIJO = "CAP-"
LARGO_ULID = 26
BITS_TIEMPO = 48
BITS_AZAR = 80
_MASCARA_TIEMPO = (1 << BITS_TIEMPO) - 1


def _milisegundos() -> int:
    """Tiempo actual en milisegundos."""
    return time.time_ns() // 1_000_000


def nuevo_ulid(ms: int | None = None) -> str:
    """ULID de 26 caracteres: tiempo arriba, azar abajo.

    Los 26 caracteres cubren 130 bits, así que el primero solo lleva los 3 bits
    que sobran del valor de 128 y nunca pasa de `7`.
    """
    milisegundos = _milisegundos() if ms is None else ms
    azar = int.from_bytes(secrets.token_bytes(BITS_AZAR // 8), "big")
    valor = ((milisegundos & _MASCARA_TIEMPO) << BITS_AZAR) | azar
    return "".join(ALFABETO[(valor >> (5 * posicion)) & 0b11111] for posicion in reversed(range(LARGO_ULID)))


def nuevo_id_captura(ms: int | None = None) -> str:
    """Id de captura nuevo, como `CAP-01M503FN5942S3MNAFA14C07AQ`."""
    return PREFIJO + nuevo_ulid(ms)


def es_id_captura(valor: str) -> bool:
    """`True` si `valor` calza con `^CAP-[0-9A-HJKMNP-TV-Z]{26}$`."""
    return bool(RE_ID_CAPTURA.match(valor))
