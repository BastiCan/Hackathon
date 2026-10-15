"""Modelos de dominio (pydantic v2) y enums de dominio.md Seccion 2.

Nota: la cantidad de niveles y de codigos NO se fija aqui; `nivel` es un entero que
sale del cruce con rubrica.json (tech.md). Estos modelos describen la forma de la
entrada, los fragmentos y las observaciones resultantes.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

# --- Enums (dominio.md Seccion 2) ---

class TipoObservacion(StrEnum):
    PARTICULAR = "PARTICULAR"
    GENERAL = "GENERAL"
    NO_IDENTIFICADO = "NO_IDENTIFICADO"


class ErrorIdentificacion(StrEnum):
    NO_ENCONTRADO = "NO_ENCONTRADO"
    AMBIGUO = "AMBIGUO"
    FUERA_DE_SALA = "FUERA_DE_SALA"


class Evaluabilidad(StrEnum):
    EVALUABLE = "EVALUABLE"
    NO_EVALUABLE = "NO_EVALUABLE"


class MotivoNoEvaluable(StrEnum):
    ESTADO_O_SALUD = "ESTADO_O_SALUD"
    JUICIO_SIN_CONDUCTA = "JUICIO_SIN_CONDUCTA"
    CONDUCTA_ADULTO = "CONDUCTA_ADULTO"
    LOGISTICA_O_FAMILIA = "LOGISTICA_O_FAMILIA"
    OTRO = "OTRO"


class Certeza(StrEnum):
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"


class ComparacionEdad(StrEnum):
    BAJO_LO_ESPERADO = "BAJO_LO_ESPERADO"
    ACORDE = "ACORDE"
    SOBRE_LO_ESPERADO = "SOBRE_LO_ESPERADO"


class EstadoObservacion(StrEnum):
    SUGERIDO = "SUGERIDO"


class EstadoRegistro(StrEnum):
    RECIBIDO = "RECIBIDO"
    PROCESANDO = "PROCESANDO"
    PROCESADO = "PROCESADO"
    SIN_TEXTO = "SIN_TEXTO"
    ERROR = "ERROR"


class ErrorCaptura(StrEnum):
    TEXTO_VACIO = "TEXTO_VACIO"
    EDUCADORA_DESCONOCIDA = "EDUCADORA_DESCONOCIDA"
    SALA_DESCONOCIDA = "SALA_DESCONOCIDA"


class ErrorEvaluacion(StrEnum):
    LLM_SALIDA_INVALIDA = "LLM_SALIDA_INVALIDA"


class TipoContenido(StrEnum):
    CONDUCTA = "conducta"
    ESTADO = "estado"
    JUICIO = "juicio"
    CONDUCTA_ADULTO = "conducta_adulto"
    LOGISTICA = "logistica"


class Iniciativa(StrEnum):
    ESPONTANEA = "espontanea"
    CON_CONSIGNA = "con_consigna"
    IMITACION = "imitacion"
    NO_SE_SABE = "no_se_sabe"


class Apoyo(StrEnum):
    SIN_AYUDA = "sin_ayuda"
    CON_APOYO_ADULTO = "con_apoyo_adulto"
    CON_APOYO_OBJETO = "con_apoyo_objeto"
    NO_SE_SABE = "no_se_sabe"


# --- Modelos base ---

class _Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Entrada y nomina ---

class Entrada(_Modelo):
    """Evento que recibe la Lambda."""

    texto: str
    id_educadora: str
    sala_grupo: str
    fecha: date


class Educadora(_Modelo):
    id_educadora: str
    id_jardin: str
    rol: str | None = None


class Nino(_Modelo):
    id_nino: str
    id_jardin: str
    sala_grupo: str
    nombre: str
    apodos: list[str] = Field(default_factory=list)
    fecha_nacimiento: date
    fecha_ingreso: date


class Candidato(_Modelo):
    """Candidato de identificacion por nombre (top 3 por similitud)."""

    id_nino: str
    nombre: str
    score: int


# --- Conductas (salida de extraer_conductas) ---

class Conducta(_Modelo):
    accion: str
    frase_literal: str
    iniciativa: Iniciativa
    apoyo: Apoyo
    complejidad: str
    tipo_contenido: TipoContenido


# --- Sugerencia / manifestacion consolidada ---

class Sugerencia(_Modelo):
    """Un codigo de manifestacion ya cruzado con rubrica.json."""

    id_manifestacion: str
    nivel: int
    dominio: str
    texto_observable: str
    frase_evidencia: str
    certeza: Certeza


# --- Observacion (registro guardado y devuelto) ---

class Observacion(_Modelo):
    id_obs: str
    tipo: TipoObservacion
    texto_literal: str

    # Identificacion
    id_nino: str | None = None
    error_identificacion: ErrorIdentificacion | None = None
    candidatos: list[Candidato] = Field(default_factory=list)

    # Evaluabilidad / evaluacion (solo PARTICULAR identificada)
    evaluabilidad: Evaluabilidad | None = None
    motivo_no_evaluable: MotivoNoEvaluable | None = None
    conductas: list[Conducta] = Field(default_factory=list)
    manifestaciones: list[Sugerencia] = Field(default_factory=list)
    nivel: int | None = None
    certeza: Certeza | None = None
    comentario: str | None = None
    otro_codigo_viable: str | None = None

    # Comparacion con la edad (solo codigo, despues de evaluar)
    edad_meses: int | None = None
    niveles_esperados: list[int] = Field(default_factory=list)
    comparacion_edad: ComparacionEdad | None = None
    fuera_de_rango_rubrica: bool = False

    # Metadatos
    fecha_en_texto: str | None = None
    archivo_s3: str | None = None  # clave S3 del archivo original de la parte, si existe
    error_evaluacion: ErrorEvaluacion | None = None
    estado: EstadoObservacion = EstadoObservacion.SUGERIDO


class Resultado(_Modelo):
    """Respuesta del pipeline para una captura procesada."""

    id_captura: str
    advertencias: list[str] = Field(default_factory=list)
    observaciones: list[Observacion] = Field(default_factory=list)


# --- Captura (entrada por S3) ---

class Meta(_Modelo):
    """Contexto de la captura (capturas/{id}/meta.json). Manda sobre las partes."""

    id_educadora: str
    sala_grupo: str
    fecha_observacion: date
    tipo: str | None = None  # tipo de nota (opcional; informativo)


class Parte(_Modelo):
    """Una parte de texto de la captura. `archivo` es relativo a la carpeta de la captura."""

    texto: str
    archivo: str | None = None


class TextoCaptura(_Modelo):
    """Contenido de capturas/{id}/texto.json."""

    id_captura: str | None = None
    fuente: str | None = None  # ocr | audio | manual
    partes: list[Parte] = Field(default_factory=list)
    # Caso compacto: {"texto": "..."} sin partes -> una unica parte sin archivo.
    texto: str | None = None

    def partes_normalizadas(self) -> list[Parte]:
        """Lista de partes a procesar; si vino solo `texto`, es una parte sin archivo."""
        if self.partes:
            return self.partes
        if self.texto is not None:
            return [Parte(texto=self.texto)]
        return []
