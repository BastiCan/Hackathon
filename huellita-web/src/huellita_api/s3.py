"""Escrituras del BFF en el bucket de capturas (SPEC-OFICIAL.md §5 y §7, CONTRATOS.md §7).

El BFF solo hace `PutObject`: `capturas/{id}/meta.json` **siempre primero** y
después `capturas/{id}/texto.json`. Si llegan al revés, ProcesarNota marca la
captura en ERROR.
"""
from __future__ import annotations

import functools
import json
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config as AjustesBoto

if TYPE_CHECKING:  # pragma: no cover - solo para los tipos
    from botocore.client import BaseClient

    from .config import Config

AJUSTES = AjustesBoto(connect_timeout=3, read_timeout=8, retries={"mode": "standard"})


@functools.cache
def cliente() -> BaseClient:
    """Cliente de S3, uno por proceso, con los tiempos límite del spec."""
    return boto3.client("s3", config=AJUSTES)


def clave_meta(id_captura: str) -> str:
    """Clave del `meta.json` de la captura."""
    return f"capturas/{id_captura}/meta.json"


def clave_texto(id_captura: str) -> str:
    """Clave del `texto.json` de la captura."""
    return f"capturas/{id_captura}/texto.json"


def clave_foto(id_captura: str, ext: str = "jpg") -> str:
    """Clave de la foto original de la captura: `capturas/{id}/original/foto.{ext}`."""
    return f"capturas/{id_captura}/original/foto.{ext}"


def cuerpo_meta(autor_id: str, sala_id: str, fecha: str) -> dict:
    """Las tres claves de `meta.json`, en este orden. `fecha` es la de Chile."""
    return {"id_educadora": autor_id, "sala_grupo": sala_id, "fecha_observacion": fecha}


def cuerpo_texto(id_captura: str, texto: str, fuente: str = "manual") -> dict:
    """Las tres claves de `texto.json`. `fuente` es `manual` o `audio`."""
    return {"id_captura": id_captura, "fuente": fuente, "partes": [{"texto": texto}]}


def subir_json(cfg: Config, clave: str, contenido: dict) -> None:
    """Sube `contenido` como JSON UTF-8. Cualquier error se propaga tal cual:
    lo traduce a `error_envio` quien llama."""
    cliente().put_object(
        Bucket=cfg.bucket_capturas,
        Key=clave,
        Body=json.dumps(contenido, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )


def subir_imagen(cfg: Config, clave: str, datos: bytes, content_type: str) -> None:
    """Sube los bytes de la foto bajo `original/`. Como `subir_json`, cualquier
    error se propaga tal cual: lo traduce a `error_envio` quien llama."""
    cliente().put_object(
        Bucket=cfg.bucket_capturas,
        Key=clave,
        Body=datos,
        ContentType=content_type,
    )
