"""Configuración de la aplicación.

Lee variables de entorno con valores por defecto pensados para la demo local.
No usamos pydantic-settings para mantener las dependencias mínimas.
"""
from __future__ import annotations

import os
from pathlib import Path

# Raíz del repositorio (dos niveles arriba de este archivo: backend/app/config.py).
REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_dataset_dir() -> Path:
    raw = os.environ.get(
        "DATASET_DIR",
        str(REPO_ROOT / "Dump" / "dataset_e1_publico" / "datos_publicos"),
    )
    path = Path(raw)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return path


DATASET_DIR: Path = _resolve_dataset_dir()
AI_PROVIDER: str = os.environ.get("AI_PROVIDER", "mock").lower()

# Umbrales de las reglas de alerta (ver §4 de la síntesis).
# Semanas sin evidencia en un núcleo antes de marcar "sin evidencia reciente".
WEEKS_WITHOUT_EVIDENCE = 4
# Observaciones coincidentes mínimas para confirmar un rezago.
MIN_OBS_TO_CONFIRM = 2
