"""Configuración del BFF, leída de variables de entorno (las define template.yaml)."""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    tabla_jardines: str
    tabla_educadoras: str
    tabla_ninos: str
    tabla_registros: str
    tabla_observaciones: str
    tabla_capturas: str
    tabla_decisiones: str
    bucket_capturas: str
    url_transcriptor: str
    id_clave_transcriptor: str
    funcion_ocr: str
    jardin: str
    salas: tuple[str, ...]
    max_capturas_dia: int
    minutos_max_procesando: int
    zona_horaria: str

    def sala_key(self, sala: str) -> str:
        """Clave de sala de integra-procesador: "JAR-0001#SG-A"."""
        return f"{self.jardin}#{sala}"


def _entero(entorno: Mapping[str, str], clave: str, defecto: int, minimo: int) -> int:
    valor = int(entorno.get(clave, str(defecto)))
    if valor < minimo:
        raise ValueError(f"{clave} debe ser mayor o igual que {minimo}")
    return valor


def cargar_config(entorno: Mapping[str, str] | None = None) -> Config:
    entorno = os.environ if entorno is None else entorno
    salas = tuple(s.strip() for s in entorno.get("SALAS_DEMO", "SG-A,SG-B").split(",") if s.strip())
    if not salas:
        raise ValueError("SALAS_DEMO no puede quedar vacía")
    return Config(
        tabla_jardines=entorno.get("TABLA_JARDINES", ""),
        tabla_educadoras=entorno.get("TABLA_EDUCADORAS", ""),
        tabla_ninos=entorno.get("TABLA_NINOS", ""),
        tabla_registros=entorno.get("TABLA_REGISTROS", ""),
        tabla_observaciones=entorno.get("TABLA_OBSERVACIONES", ""),
        tabla_capturas=entorno.get("TABLA_CAPTURAS", ""),
        tabla_decisiones=entorno.get("TABLA_DECISIONES", ""),
        bucket_capturas=entorno.get("BUCKET_CAPTURAS", ""),
        url_transcriptor=entorno.get("URL_TRANSCRIPTOR", "").rstrip("/"),
        id_clave_transcriptor=entorno.get("ID_CLAVE_TRANSCRIPTOR", ""),
        funcion_ocr=entorno.get("FUNCION_OCR", ""),
        jardin=entorno.get("JARDIN_DEMO", "JAR-0001"),
        salas=salas,
        max_capturas_dia=_entero(entorno, "MAX_CAPTURAS_DIA", 300, 1),
        minutos_max_procesando=_entero(entorno, "MINUTOS_MAX_PROCESANDO", 20, 1),
        zona_horaria=entorno.get("ZONA_HORARIA", "America/Santiago"),
    )
