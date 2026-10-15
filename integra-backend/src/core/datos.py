"""Acceso a datos: nomina/educadora y guardado de observaciones.

Dos implementaciones con la misma interfaz:
- `DatosLocal` (esta etapa): lee tests/fixtures/nomina_demo.json y guarda en memoria.
- `DatosDynamo` (tarea 8): DynamoDB.

El pipeline recibe un objeto `Datos` y no sabe de donde salen los datos (FUENTE_DATOS).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Protocol

from .config import RAIZ, config
from .modelos import Educadora, Nino, Observacion

NOMINA_DEMO = RAIZ / "tests" / "fixtures" / "nomina_demo.json"


class Datos(Protocol):
    """Interfaz de acceso a datos usada por el pipeline."""

    def educadora(self, id_educadora: str) -> Educadora | None: ...

    def ninos_de_jardin(self, id_jardin: str) -> list[Nino]: ...

    def guardar_observaciones(
        self,
        observaciones: list[Observacion],
        id_captura: str = "",
        cabecera: dict | None = None,
    ) -> None: ...


def _parse_nino(d: dict) -> Nino:
    return Nino(
        id_nino=d["id_nino"],
        id_jardin=d["id_jardin"],
        sala_grupo=d["sala_grupo"],
        nombre=d["nombre"],
        apodos=d.get("apodos", []),
        fecha_nacimiento=date.fromisoformat(d["fecha_nacimiento"]),
        fecha_ingreso=date.fromisoformat(d["fecha_ingreso"]),
    )


class DatosLocal:
    """Implementacion local: nomina desde nomina_demo.json, guardado en memoria."""

    def __init__(self, ruta_nomina: str | Path = NOMINA_DEMO) -> None:
        with Path(ruta_nomina).open(encoding="utf-8") as f:
            datos = json.load(f)
        self._educadoras: dict[str, Educadora] = {
            e["id_educadora"]: Educadora(id_educadora=e["id_educadora"], id_jardin=e["id_jardin"])
            for e in datos.get("educadoras", [])
        }
        self._ninos: list[Nino] = [_parse_nino(n) for n in datos.get("ninos", [])]
        self.guardadas: list[Observacion] = []

    def educadora(self, id_educadora: str) -> Educadora | None:
        return self._educadoras.get(id_educadora)

    def ninos_de_jardin(self, id_jardin: str) -> list[Nino]:
        return [n for n in self._ninos if n.id_jardin == id_jardin]

    def guardar_observaciones(
        self,
        observaciones: list[Observacion],
        id_captura: str = "",
        cabecera: dict | None = None,
    ) -> None:
        # En local se ignora la cabecera de captura (solo se guarda en memoria).
        self.guardadas.extend(observaciones)


def crear_datos() -> Datos:
    """Fabrica segun FUENTE_DATOS. En esta etapa solo 'local'; 'aws' llega en tarea 8."""
    if config.es_local:
        return DatosLocal()
    # La implementacion DynamoDB se agrega en la tarea 8.
    from .datos_aws import DatosDynamo

    return DatosDynamo()
