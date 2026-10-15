"""Contrato JSON que entrega el transcriptor.

Es el mismo de contrato/resultado_transcripcion.schema.json. Sigue la estructura
TextoTranscrito de design.md y agrega id_captura, origen, estado y error.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

PATRON_ID_CAPTURA = r"^[A-Za-z0-9._-]{1,128}$"
PATRON_ID_TRABAJO = r"^[A-Za-z0-9._-]{1,200}$"

Estado = Literal["transcribiendo", "completado", "fallido"]
Idioma = Literal["es-US", "es-MX", "es-ES"]
Confianza = Annotated[float, Field(ge=0, le=1)]


class Palabra(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texto: str
    inicio_segundos: float | None
    fin_segundos: float | None
    confianza: Confianza
    dudosa: bool


class ErrorResultado(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str
    mensaje: str


class ResultadoTranscripcion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_captura: str
    origen: Literal["audio", "postit"]
    estado: Estado
    texto_completo: str
    palabras: list[Palabra]
    confianza_agregada: Confianza | None
    idioma: Idioma
    proveedor: str
    modelo: str
    id_trabajo: str
    iniciado_en: str
    terminado_en: str | None
    error: ErrorResultado | None


class SolicitudAudio(BaseModel):
    """Cuerpo de POST /api/transcripciones/audio."""

    id_captura: str = Field(
        pattern=PATRON_ID_CAPTURA,
        description="ID de la captura en el otro backend. Es la clave de idempotencia.",
    )
    audio_base64: str = Field(description="Audio en base64 estándar. Acepta el prefijo data:audio/...;base64,")
    idioma: Idioma | None = Field(default=None, description="Opcional. Por defecto, TRANSCRIBE_IDIOMA.")


class RespuestaError(BaseModel):
    error: ErrorResultado