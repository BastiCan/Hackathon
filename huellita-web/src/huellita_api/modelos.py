"""Contratos de la API, con los mismos nombres de campos que los tipos de Huellita
(huellita-formato-mejorado/src/lib/tipos.ts). Los campos opcionales que vienen en
None no se envían: en TypeScript quedan como `undefined`."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

NucleoId = Literal["motor_grueso", "motor_fino", "lenguaje_comunicacion", "socioemocional", "cognitivo"]
NUCLEOS: tuple[str, ...] = ("motor_grueso", "motor_fino", "lenguaje_comunicacion", "socioemocional", "cognitivo")
Nivel = Annotated[int, Field(ge=1, le=9)]
Certeza = Literal["alta", "media", "baja"]
EstadoSugerencia = Literal["pendiente", "aceptada", "cambiada", "descartada"]
EstadoEvidencia = Literal["procesando", "lista", "error"]
Formato = Literal["foto", "audio", "texto"]
NivelEducativo = Literal[
    "Sala Cuna Menor", "Sala Cuna Mayor", "Medio Menor", "Medio Mayor", "Transición 1", "Transición 2"
]


class _Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Jardin(_Modelo):
    id: str
    nombre: str
    comuna: str
    region: str


class Sala(_Modelo):
    id: str
    jardinId: str
    nombre: str
    nivelEducativo: NivelEducativo


class Usuaria(_Modelo):
    id: str
    nombre: str
    rol: Literal["tia", "directora"]
    jardinId: str
    salaIds: list[str]


class Nino(_Modelo):
    id: str
    nombre: str
    apellidoInicial: str
    fechaNacimiento: str
    salaId: str
    activo: bool


class Evidencia(_Modelo):
    id: str
    salaId: str
    autorId: str
    creadaEn: str
    formato: Formato
    ninoIdSugerido: str | None = None
    textoExtraido: str | None = None
    foto: str | None = None
    estado: EstadoEvidencia


class Original(_Modelo):
    ninoId: str | None = None
    nucleo: NucleoId | None = None
    nivel: Nivel | None = None


class Sugerencia(_Modelo):
    id: str
    evidenciaId: str
    salaId: str
    tipo: Literal["evaluacion", "nota_sala"]
    ninoId: str | None = None
    nombreDetectado: str | None = None
    nucleo: NucleoId | None = None
    nivel: Nivel | None = None
    conducta: str | None = None
    cita: str
    certeza: Certeza
    estado: EstadoSugerencia
    validadaPor: str | None = None
    validadaEn: str | None = None
    original: Original | None = None


class Contexto(_Modelo):
    jardin: Jardin
    salas: list[Sala]
    usuarias: list[Usuaria]


class Registros(_Modelo):
    """Evidencias (en orden de llegada) y sugerencias de una sala."""

    evidencias: list[Evidencia]
    sugerencias: list[Sugerencia]


class CapturaEntrada(_Modelo):
    salaId: str
    autorId: str
    formato: str
    texto: str | None = None
    audioBase64: str | None = None
    mimeType: str | None = None
    ninoIdSugerido: str | None = None


class CapturaCreada(_Modelo):
    evidencia: Evidencia


class Cambios(_Modelo):
    ninoId: str
    nucleo: NucleoId
    nivel: Nivel


class ItemDecision(_Modelo):
    idSugerencia: str
    estado: Literal["aceptada", "descartada", "pendiente"]
    cambios: Cambios | None = None


class DecisionesEntrada(_Modelo):
    salaId: str
    usuariaId: str
    items: list[ItemDecision] = Field(min_length=1, max_length=50)


class SugerenciasActualizadas(_Modelo):
    sugerencias: list[Sugerencia]


class DetalleError(_Modelo):
    codigo: str
    mensaje: str


class RespuestaError(_Modelo):
    error: DetalleError
