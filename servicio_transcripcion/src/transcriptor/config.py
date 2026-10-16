"""Configuración del servicio, leída de variables de entorno (ver README)."""
from __future__ import annotations

import os
from dataclasses import dataclass

IDIOMAS = ("es-US", "es-MX", "es-ES")  # Transcribe no tiene es-CL


@dataclass(frozen=True)
class Config:
    bucket: str = ""
    idioma: str = "es-US"
    umbral_palabra_dudosa: float = 0.60
    # El audio llega en base64 dentro del JSON y el evento debe caber en los 6 MB de Lambda.
    max_bytes_audio: int = 4 * 1024 * 1024
    prefijo_trabajo: str = "tr-"
    # Bucket de entrada de ProcesarNota. Vacío: no se entrega texto.json.
    bucket_capturas: str = ""
    modo_mock: bool = False


def cargar_config() -> Config:
    """Lee y valida la configuración. Lanza ValueError si algo está mal."""
    config = Config(
        bucket=os.getenv("BUCKET", ""),
        idioma=os.getenv("TRANSCRIBE_IDIOMA", "es-US"),
        umbral_palabra_dudosa=float(os.getenv("UMBRAL_PALABRA_DUDOSA", "0.60")),
        max_bytes_audio=int(os.getenv("MAX_BYTES_AUDIO", str(4 * 1024 * 1024))),
        prefijo_trabajo=os.getenv("PREFIJO_TRABAJO", "tr-"),
        bucket_capturas=os.getenv("BUCKET_CAPTURAS", ""),
        modo_mock=os.getenv("MODO_MOCK", "0").strip().lower() in ("1", "true", "si", "sí"),
    )
    if config.idioma not in IDIOMAS:
        raise ValueError(f"TRANSCRIBE_IDIOMA debe ser uno de: {', '.join(IDIOMAS)}")
    if not 0 <= config.umbral_palabra_dudosa <= 1:
        raise ValueError("UMBRAL_PALABRA_DUDOSA debe estar entre 0 y 1")
    if not config.prefijo_trabajo:
        raise ValueError("PREFIJO_TRABAJO no puede estar vacío")
    if not config.modo_mock and not config.bucket:
        raise ValueError("Falta BUCKET. Para probar sin AWS use MODO_MOCK=1")
    return config