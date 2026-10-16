"""La hora de Chile: una sola fuente para las fechas y los vencimientos.

Todo lo que necesite la hora recibe un `Reloj` o un `datetime` ya resuelto, así las pruebas
pueden inyectar el momento exacto sin esperar.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import Config

Reloj = Callable[[], datetime]


def ahora(cfg: Config) -> datetime:
    """Ahora en la zona del jardín (`cfg.zona_horaria`, con `tzdata`)."""
    return datetime.now(ZoneInfo(cfg.zona_horaria))


def reloj_de(cfg: Config, reloj: Reloj | None) -> datetime:
    """El momento del reloj inyectado, o el de verdad si no viene ninguno."""
    return reloj() if reloj is not None else ahora(cfg)


def iso(momento: datetime) -> str:
    """ISO-8601 con huso y sin microsegundos: "2026-10-15T14:05:57-03:00"."""
    return momento.isoformat(timespec="seconds")


def dia(momento: datetime) -> str:
    """La fecha del momento: "2026-10-15"."""
    return momento.date().isoformat()


def minutos_desde(creada_en: str, momento: datetime) -> float:
    """Minutos entre una marca ISO y `momento`.

    Si la marca no trae huso se asume el de `momento`; si no se puede leer devuelve `0.0`,
    es decir, no vence.
    """
    try:
        marca = datetime.fromisoformat(creada_en)
    except (TypeError, ValueError):
        return 0.0
    if marca.tzinfo is None:
        marca = marca.replace(tzinfo=momento.tzinfo)
    return (momento - marca).total_seconds() / 60
