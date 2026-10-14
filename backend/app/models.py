"""Modelos Pydantic que describen las entidades del dominio y las respuestas de la API."""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel

AlertState = Literal["al_dia", "sin_evidencia", "posible_rezago", "ingreso_reciente"]
Dominio = Literal[
    "motor_grueso",
    "motor_fino",
    "lenguaje_comunicacion",
    "socioemocional",
    "cognitivo",
]


class Jardin(BaseModel):
    id_jardin: str
    nombre_fantasia: str
    comuna: str
    region: str
    numero_salas: int
    numero_educadoras: int


class Educadora(BaseModel):
    id_educadora: str
    id_jardin: str
    rol: str
    anios_experiencia: int


class Nino(BaseModel):
    id_nino: str
    fecha_nacimiento: date
    sexo_registrado: str
    id_jardin: str
    sala_grupo: str
    fecha_ingreso: date


class NivelRuta(BaseModel):
    nivel: int
    nombre_nivel: str
    edad_min_meses: int
    edad_max_meses: int
    dominios: list[str]
    descripcion: str


class Manifestacion(BaseModel):
    id_manifestacion: str
    nivel: int
    dominio: Dominio
    texto_observable: str


class Observacion(BaseModel):
    id_observacion: str
    id_nino: str
    id_educadora: str
    fecha_observacion: date
    formato_captura: str
    nivel_estimado: int
    nota_breve: Optional[str] = None


# ---- Respuestas compuestas ----

class NinoEstado(BaseModel):
    """Niño con su estado agregado para la vista de sala (semáforo)."""
    nino: Nino
    edad_meses: int
    ultima_observacion: Optional[date]
    nivel_actual: Optional[int]
    estado: AlertState
    dias_sin_evidencia: Optional[int]


class Alerta(BaseModel):
    id_nino: str
    tipo: Literal["sin_evidencia", "posible_rezago"]
    severidad: Literal["media", "alta"]
    mensaje: str
    accion_sugerida: str
    nucleos_afectados: list[str]
    confirmada: bool


class MisionItem(BaseModel):
    id_nino: str
    motivo: str
    dominio_sugerido: Optional[str]
    que_observar: Optional[str]


# ---- IA: captura y sugerencia ----

class CapturaRequest(BaseModel):
    texto: str
    id_educadora: Optional[str] = None


class SugerenciaIA(BaseModel):
    id_nino_sugerido: Optional[str]
    nombre_detectado: Optional[str]
    es_evaluable: bool
    dominio: Optional[Dominio]
    nivel_sugerido: Optional[int]
    manifestacion_sugerida: Optional[str]
    certeza: Literal["alta", "media", "baja"]
    evidencia: str


class ProcesarCapturaResponse(BaseModel):
    sugerencias: list[SugerenciaIA]
