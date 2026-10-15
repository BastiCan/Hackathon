"""Carga de los recursos JSON (rubrica, fewshot, embeddings) desde local o S3.

Segun FUENTE_DATOS:
- local: lee data/processed/*.json
- aws:   lee s3://<BUCKET>/rubrica/*.json

Centraliza la decision para que el handler (Lambda) y los scripts no la repitan.
Los prefijos en S3 siguen design.md: rubrica/rubrica.json, rubrica/fewshot.json,
rubrica/embeddings_rubrica.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import EMBEDDINGS_LOCAL, FEWSHOT_LOCAL, RUBRICA_LOCAL, config

# Nombre logico -> (ruta local, clave S3 bajo rubrica/).
_RECURSOS = {
    "rubrica": (RUBRICA_LOCAL, "rubrica/rubrica.json"),
    "fewshot": (FEWSHOT_LOCAL, "rubrica/fewshot.json"),
    "embeddings": (EMBEDDINGS_LOCAL, "rubrica/embeddings_rubrica.json"),
}

_cliente_s3 = None


def _s3():
    global _cliente_s3
    if _cliente_s3 is None:
        import boto3

        _cliente_s3 = boto3.client("s3", region_name=config.region)
    return _cliente_s3


def cargar_json(nombre: str) -> dict[str, Any]:
    """Devuelve el recurso JSON parseado (local o S3 segun FUENTE_DATOS)."""
    if nombre not in _RECURSOS:
        raise KeyError(f"recurso desconocido: {nombre}")
    ruta_local, clave_s3 = _RECURSOS[nombre]

    if config.es_local:
        with Path(ruta_local).open(encoding="utf-8") as f:
            return json.load(f)

    if not config.bucket:
        raise ValueError("falta BUCKET en el entorno para cargar recursos desde S3")
    resp = _s3().get_object(Bucket=config.bucket, Key=clave_s3)
    return json.loads(resp["Body"].read())


def leer_json_s3(bucket: str, clave: str) -> dict[str, Any]:
    """Lee y parsea un objeto JSON arbitrario de S3 (usado por el handler para capturas)."""
    resp = _s3().get_object(Bucket=bucket, Key=clave)
    return json.loads(resp["Body"].read())
