"""Capa de IA con interfaz estable.

La API del backend llama a `procesar_captura(...)` sin saber qué proveedor hay
detrás. Hoy existe un proveedor "mock" determinista que no necesita red (ideal
para la demo); mañana se puede añadir uno "bedrock" implementando la misma firma.

El mock hace, de forma heurística, lo que haría el modelo real:
1. Separa el texto en frases por niño.
2. Identifica al niño cruzando el nombre contra la lista de la sala + apodos.
3. Decide si la frase es evaluable (filtra notas grupales / no evaluables).
4. Sugiere dominio, nivel y manifestación, con certeza y evidencia textual.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date

from ..config import AI_PROVIDER
from ..data import DataStore
from ..models import Nino, SugerenciaIA
from .analytics import edad_meses, nivel_esperado_para_edad

# Palabras que suelen marcar una nota grupal / no evaluable (se descartan).
_FRASES_NO_EVALUABLES = (
    "los niños",
    "el grupo",
    "la sala",
    "bajó la asistencia",
    "hoy hubo",
    "esta semana",
)

# Pistas léxicas → dominio, para orientar la sugerencia del mock.
_PISTAS_DOMINIO: dict[str, list[str]] = {
    "lenguaje_comunicacion": ["dijo", "dice", "palabra", "nombr", "cuenta", "conversa"],
    "motor_grueso": ["camin", "corr", "salt", "sube", "baja", "equilibr", "circuito"],
    "motor_fino": ["agarr", "recog", "encaj", "dibuj", "pinz", "manipul", "orden"],
    "socioemocional": ["compart", "ayud", "turno", "espera", "llor", "calm", "pares"],
    "cognitivo": ["clasific", "color", "tamaño", "cuenta", "arma", "resuelv", "busca"],
}


def _normalizar(texto: str) -> str:
    s = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _separar_frases(texto: str) -> list[str]:
    partes = re.split(r"[.\n;]+", texto)
    return [p.strip() for p in partes if p.strip()]


def _es_evaluable(frase_norm: str) -> bool:
    return not any(_normalizar(f) in frase_norm for f in _FRASES_NO_EVALUABLES)


def _detectar_dominio(frase_norm: str) -> str | None:
    for dominio, pistas in _PISTAS_DOMINIO.items():
        if any(p in frase_norm for p in pistas):
            return dominio
    return None


def _construir_indice_nombres(ninos: list[Nino]) -> dict[str, str]:
    """Mapa nombre_normalizado -> id_nino.

    El dataset no trae nombres (solo IDs tipo NINO-00001), así que indexamos por
    el sufijo numérico y por el id completo. En producción aquí entraría el
    diccionario de apodos de la sala.
    """
    indice: dict[str, str] = {}
    for n in ninos:
        indice[_normalizar(n.id_nino)] = n.id_nino
        sufijo = n.id_nino.split("-")[-1].lstrip("0") or "0"
        indice[sufijo] = n.id_nino
    return indice


def _identificar_nino(frase_norm: str, indice: dict[str, str]) -> tuple[str | None, str | None]:
    tokens = set(re.findall(r"[a-z0-9\-]+", frase_norm))
    # Primero intentamos coincidencia por token exacto (nombre/número aislado).
    for clave, id_nino in indice.items():
        if clave in tokens:
            return id_nino, clave
    # Luego, coincidencia por subcadena (p. ej. el id completo "nino-00001").
    for clave, id_nino in indice.items():
        if len(clave) >= 3 and clave in frase_norm:
            return id_nino, clave
    return None, None


def _mock_procesar(
    store: DataStore, texto: str, ninos_sala: list[Nino], hoy: date
) -> list[SugerenciaIA]:
    indice = _construir_indice_nombres(ninos_sala)
    por_id = {n.id_nino: n for n in ninos_sala}
    sugerencias: list[SugerenciaIA] = []

    for frase in _separar_frases(texto):
        frase_norm = _normalizar(frase)
        evaluable = _es_evaluable(frase_norm)
        id_nino, nombre = _identificar_nino(frase_norm, indice)
        dominio = _detectar_dominio(frase_norm)

        nivel_sugerido: int | None = None
        manifestacion: str | None = None
        certeza = "baja"

        if evaluable and id_nino and id_nino in por_id:
            nino = por_id[id_nino]
            meses = edad_meses(nino.fecha_nacimiento, hoy)
            nivel_sugerido = nivel_esperado_para_edad(store, meses)
            if nivel_sugerido is not None and dominio:
                manifs = [
                    m
                    for m in store.manifestaciones_de_nivel(nivel_sugerido)
                    if m.dominio == dominio
                ]
                if manifs:
                    manifestacion = manifs[0].texto_observable
                    certeza = "media" if dominio else "baja"
            if dominio and nivel_sugerido is not None:
                certeza = "alta" if manifestacion else "media"

        sugerencias.append(
            SugerenciaIA(
                id_nino_sugerido=id_nino,
                nombre_detectado=nombre,
                es_evaluable=evaluable,
                dominio=dominio,  # type: ignore[arg-type]
                nivel_sugerido=nivel_sugerido,
                manifestacion_sugerida=manifestacion,
                certeza=certeza,  # type: ignore[arg-type]
                evidencia=frase,
            )
        )
    return sugerencias


def procesar_captura(
    store: DataStore,
    texto: str,
    ninos_sala: list[Nino],
    hoy: date,
) -> list[SugerenciaIA]:
    """Punto de entrada único para la API. Enruta según el proveedor configurado."""
    if AI_PROVIDER == "mock":
        return _mock_procesar(store, texto, ninos_sala, hoy)
    # Espacio para `if AI_PROVIDER == "bedrock": ...` sin tocar la API.
    raise NotImplementedError(
        f"Proveedor de IA no soportado: {AI_PROVIDER!r}. Usa AI_PROVIDER=mock."
    )
