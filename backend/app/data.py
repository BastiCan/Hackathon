"""Carga del dataset sintético E-1 en memoria.

Usa solo la biblioteca estándar (módulo csv). El dataset es pequeño (cientos de
niños, miles de observaciones), así que se carga completo una vez al iniciar.
"""
from __future__ import annotations

import csv
from datetime import date
from functools import lru_cache
from pathlib import Path

from .config import DATASET_DIR
from .models import (
    Educadora,
    Jardin,
    Manifestacion,
    Nino,
    NivelRuta,
    Observacion,
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


class DataStore:
    """Contenedor en memoria con índices útiles para consultas frecuentes."""

    def __init__(self, dataset_dir: Path):
        self.dataset_dir = dataset_dir
        self.jardines: dict[str, Jardin] = {}
        self.educadoras: dict[str, Educadora] = {}
        self.ninos: dict[str, Nino] = {}
        self.niveles: dict[int, NivelRuta] = {}
        self.manifestaciones: dict[str, Manifestacion] = {}
        self.observaciones: list[Observacion] = []
        self._obs_por_nino: dict[str, list[Observacion]] = {}
        self._load()

    def _load(self) -> None:
        if not self.dataset_dir.exists():
            raise FileNotFoundError(
                f"No se encontró el directorio del dataset: {self.dataset_dir}"
            )

        for row in _read_csv(self.dataset_dir / "jardines.csv"):
            self.jardines[row["id_jardin"]] = Jardin(
                id_jardin=row["id_jardin"],
                nombre_fantasia=row["nombre_fantasia"],
                comuna=row["comuna"],
                region=row["region"],
                numero_salas=int(row["numero_salas"]),
                numero_educadoras=int(row["numero_educadoras"]),
            )

        for row in _read_csv(self.dataset_dir / "educadoras.csv"):
            self.educadoras[row["id_educadora"]] = Educadora(
                id_educadora=row["id_educadora"],
                id_jardin=row["id_jardin"],
                rol=row["rol"],
                anios_experiencia=int(row["anios_experiencia"]),
            )

        for row in _read_csv(self.dataset_dir / "ninos.csv"):
            self.ninos[row["id_nino"]] = Nino(
                id_nino=row["id_nino"],
                fecha_nacimiento=_parse_date(row["fecha_nacimiento"]),
                sexo_registrado=row["sexo_registrado"],
                id_jardin=row["id_jardin"],
                sala_grupo=row["sala_grupo"],
                fecha_ingreso=_parse_date(row["fecha_ingreso"]),
            )

        for row in _read_csv(self.dataset_dir / "ruta_niveles.csv"):
            self.niveles[int(row["nivel"])] = NivelRuta(
                nivel=int(row["nivel"]),
                nombre_nivel=row["nombre_nivel"],
                edad_min_meses=int(row["edad_min_meses"]),
                edad_max_meses=int(row["edad_max_meses"]),
                dominios=row["dominios"].split("|"),
                descripcion=row["descripcion"],
            )

        for row in _read_csv(self.dataset_dir / "manifestaciones.csv"):
            self.manifestaciones[row["id_manifestacion"]] = Manifestacion(
                id_manifestacion=row["id_manifestacion"],
                nivel=int(row["nivel"]),
                dominio=row["dominio"],  # type: ignore[arg-type]
                texto_observable=row["texto_observable"],
            )

        for row in _read_csv(self.dataset_dir / "observaciones.csv"):
            obs = Observacion(
                id_observacion=row["id_observacion"],
                id_nino=row["id_nino"],
                id_educadora=row["id_educadora"],
                fecha_observacion=_parse_date(row["fecha_observacion"]),
                formato_captura=row["formato_captura"],
                nivel_estimado=int(row["nivel_estimado"]),
                nota_breve=row["nota_breve"] or None,
            )
            self.observaciones.append(obs)
            self._obs_por_nino.setdefault(obs.id_nino, []).append(obs)

        # Ordenar observaciones de cada niño por fecha ascendente.
        for lista in self._obs_por_nino.values():
            lista.sort(key=lambda o: o.fecha_observacion)

    # ---- Consultas ----

    def observaciones_de(self, id_nino: str) -> list[Observacion]:
        return self._obs_por_nino.get(id_nino, [])

    def ninos_de_jardin(self, id_jardin: str) -> list[Nino]:
        return [n for n in self.ninos.values() if n.id_jardin == id_jardin]

    def ninos_de_sala(self, id_jardin: str, sala_grupo: str) -> list[Nino]:
        return [
            n
            for n in self.ninos.values()
            if n.id_jardin == id_jardin and n.sala_grupo == sala_grupo
        ]

    def manifestaciones_de_nivel(self, nivel: int) -> list[Manifestacion]:
        return [m for m in self.manifestaciones.values() if m.nivel == nivel]


@lru_cache(maxsize=1)
def get_store() -> DataStore:
    """Devuelve el DataStore cargado (singleton perezoso)."""
    return DataStore(DATASET_DIR)
