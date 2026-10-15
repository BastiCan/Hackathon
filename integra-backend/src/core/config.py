"""Configuracion del procesador de notas.

Lee variables de entorno (tech.md) y expone una instancia `config` lista para usar.
No carga datos ni habla con AWS: solo resuelve parametros. La carga de la rubrica
desde S3 o desde `data/processed/` segun `FUENTE_DATOS` se arma en tareas posteriores.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Raiz del proyecto (integra-backend/), tres niveles sobre este archivo:
# src/core/config.py -> src/core -> src -> integra-backend/
RAIZ = Path(__file__).resolve().parents[2]
DATA_PROCESSED = RAIZ / "data" / "processed"
DATA_RAW = RAIZ / "data" / "raw"

# En desarrollo local, cargar integra-backend/.env si existe (override=False: no pisa
# lo que ya este en el entorno). En Lambda no hay .env ni python-dotenv: manda el rol IAM.
_ENV_FILE = RAIZ / ".env"
if _ENV_FILE.is_file():
    try:
        from dotenv import load_dotenv

        load_dotenv(_ENV_FILE, override=False)
    except ImportError:
        pass

RUBRICA_LOCAL = DATA_PROCESSED / "rubrica.json"
FEWSHOT_LOCAL = DATA_PROCESSED / "fewshot.json"
EMBEDDINGS_LOCAL = DATA_PROCESSED / "embeddings_rubrica.json"

# Fuente de datos: 'local' lee data/processed/ y los fixtures; 'aws' usa S3/DynamoDB.
FUENTE_LOCAL = "local"
FUENTE_AWS = "aws"


def _entero(nombre: str, defecto: int) -> int:
    valor = os.environ.get(nombre)
    if valor is None or valor.strip() == "":
        return defecto
    try:
        return int(valor)
    except ValueError:
        return defecto


def _region() -> str:
    # Preferir AWS_REGION; si no existe, AWS_DEFAULT_REGION; default us-east-1.
    return (
        os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or "us-east-1"
    )


@dataclass(frozen=True)
class Config:
    """Parametros de ejecucion resueltos desde el entorno."""

    fuente_datos: str = field(default_factory=lambda: os.environ.get("FUENTE_DATOS", FUENTE_AWS).lower())
    region: str = field(default_factory=_region)

    # IDs de modelo (solo por entorno; sin valores por defecto, se pasan en tarea 4).
    model_id_separar: str | None = field(default_factory=lambda: os.environ.get("MODEL_ID_SEPARAR"))
    model_id_conductas: str | None = field(default_factory=lambda: os.environ.get("MODEL_ID_CONDUCTAS"))
    model_id_evaluar: str | None = field(default_factory=lambda: os.environ.get("MODEL_ID_EVALUAR"))
    model_id_embeddings: str | None = field(default_factory=lambda: os.environ.get("MODEL_ID_EMBEDDINGS"))

    # Tablas DynamoDB y buckets S3 (solo relevantes con FUENTE_DATOS=aws).
    tabla_jardines: str | None = field(default_factory=lambda: os.environ.get("TABLA_JARDINES"))
    tabla_educadoras: str | None = field(default_factory=lambda: os.environ.get("TABLA_EDUCADORAS"))
    tabla_ninos: str | None = field(default_factory=lambda: os.environ.get("TABLA_NINOS"))
    tabla_registros: str | None = field(default_factory=lambda: os.environ.get("TABLA_REGISTROS"))
    tabla_observaciones: str | None = field(default_factory=lambda: os.environ.get("TABLA_OBSERVACIONES"))
    bucket: str | None = field(default_factory=lambda: os.environ.get("BUCKET"))
    bucket_capturas: str | None = field(default_factory=lambda: os.environ.get("BUCKET_CAPTURAS"))

    # Parametros del pipeline.
    n_corridas_evaluar: int = field(default_factory=lambda: _entero("N_CORRIDAS_EVALUAR", 3))
    top_k: int = field(default_factory=lambda: _entero("TOP_K", 8))
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO").upper())

    @property
    def es_local(self) -> bool:
        return self.fuente_datos == FUENTE_LOCAL


def cargar_config() -> Config:
    """Construye un Config leyendo el entorno en el momento de la llamada."""
    return Config()


# Instancia por conveniencia para el import directo.
config = cargar_config()
