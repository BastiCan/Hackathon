"""Contrato de una captura con `integra-backend`: id, claves S3, petición, meta.json y texto.json.

- El id se genera como el equipo: f"CAP-{ULID()}" (python-ulid) y se valida con
  `capturas.es_id_captura` del equipo más un `re.fullmatch` (el regex del equipo usa `re.match`
  con `$`, que acepta un "\\n" final).
- Todas las claves salen de `capturas.clave_archivo` del equipo, así coinciden con el
  `archivo_s3` que guarda ProcesarNota:
      capturas/{id}/original/foto.jpg        foto completa
      capturas/{id}/original/postit_NN.jpg   recorte N (orden de lectura, desde 1)
      capturas/{id}/original/overlay.jpg     overlay numerado
      capturas/{id}/meta.json                contexto (solo si no existe)
      capturas/{id}/texto.json               una parte por post-it, siempre al final
- `capturas.py` del equipo: en local se carga el archivo real de `../integra-backend/src/core/`;
  en Lambda, la copia `capturas_equipo.py` que pone empaquetar_zip.ps1 en el zip.
"""

from __future__ import annotations

import importlib.util
import re
from datetime import date, datetime
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo

from ulid import ULID


def _cargar_capturas_equipo():
    ruta = Path(__file__).resolve().parents[1] / "integra-backend" / "src" / "core" / "capturas.py"
    if ruta.is_file():
        spec = importlib.util.spec_from_file_location("capturas_equipo", ruta)
        modulo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modulo)
        return modulo
    import capturas_equipo  # copia del zip de Lambda

    return capturas_equipo


capturas_equipo = _cargar_capturas_equipo()

ZONA = ZoneInfo("America/Santiago")
FECHA_MIN = date(2020, 1, 1)
RELATIVO_FOTO = "original/foto.jpg"
RELATIVO_OVERLAY = "original/overlay.jpg"
RELATIVO_META = "meta.json"
RELATIVO_TEXTO = "texto.json"
ORIGENES_FOTO = ("original/foto.jpg", "original/foto.jpeg", "original/foto.png")
LEGIBILIDADES = ("alta", "media", "baja")
MODOS = ("opencv", "llm")

_RE_ID = re.compile(r"CAP-[0-9A-HJKMNP-TV-Z]{26}")
_RE_CAMPO = re.compile(r"[A-Za-z0-9_-]{1,64}")
_RE_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")
_RE_S3_KEY = re.compile(r"capturas/[A-Za-z0-9!_.*'()/-]+")
_RE_RESERVADO = re.compile(r"(postit_\d+|overlay)\.jpg", re.IGNORECASE)
_EXT_OK = (".jpg", ".jpeg", ".png")
_EXT_HEIC = (".heic", ".heif")


class ErrorPeticion(Exception):
    """Petición inválida. `codigo` es PETICION_INVALIDA o FORMATO_NO_SOPORTADO; `campo` nunca lleva el valor."""

    def __init__(self, campo: str, codigo: str = "PETICION_INVALIDA"):
        super().__init__(f"campo invalido: {campo}")
        self.campo = campo
        self.codigo = codigo


class MetaInvalida(ValueError):
    """meta.json existente que Meta del equipo también rechazaría."""

    def __init__(self, campo: str):
        super().__init__(f"meta.json invalido: {campo}")
        self.campo = campo


class MetaLeida(NamedTuple):
    id_educadora: str
    sala_grupo: str
    fecha: date | None
    fecha_no_estandar: bool


# ----------------------------------------------------------------------------- id y claves

def es_id_valido(valor) -> bool:
    return (isinstance(valor, str) and _RE_ID.fullmatch(valor) is not None
            and capturas_equipo.es_id_captura(valor))


def nuevo_id_captura() -> str:
    id_captura = f"CAP-{ULID()}"
    if not es_id_valido(id_captura):  # no debería pasar nunca: mismo alfabeto Crockford
        raise RuntimeError("python-ulid genero un id que el equipo no acepta")
    return id_captura


def clave(id_captura: str, relativo: str) -> str:
    return capturas_equipo.clave_archivo(id_captura, relativo)


def prefijo(id_captura: str) -> str:
    return clave(id_captura, "")


def relativo_postit(n: int) -> str:
    return f"original/postit_{n:02d}.jpg"


# ----------------------------------------------------------------------------- fechas

def hoy_chile() -> date:
    return datetime.now(ZONA).date()


def validar_fecha(valor, campo: str = "fecha_observacion") -> date:
    if not isinstance(valor, str) or _RE_FECHA.fullmatch(valor) is None:
        raise ErrorPeticion(campo)
    try:
        fecha = date.fromisoformat(valor)
    except ValueError:
        raise ErrorPeticion(campo) from None
    if not FECHA_MIN <= fecha <= hoy_chile():
        raise ErrorPeticion(campo)
    return fecha


# ----------------------------------------------------------------------------- petición

def validar_s3_key(valor) -> tuple[str, str | None]:
    """(clave, id de la carpeta o None). Lanza ErrorPeticion."""
    if not isinstance(valor, str) or len(valor) > 1024:
        raise ErrorPeticion("s3_key")
    minus = valor.lower()
    if minus.endswith(_EXT_HEIC):
        raise ErrorPeticion("s3_key", "FORMATO_NO_SOPORTADO")
    if _RE_S3_KEY.fullmatch(valor) is None or not minus.endswith(_EXT_OK):
        raise ErrorPeticion("s3_key")
    segmentos = valor.split("/")
    if any(s in ("", ".", "..") for s in segmentos):
        raise ErrorPeticion("s3_key")
    if not segmentos[1].startswith("CAP-"):
        return valor, None
    id_captura = segmentos[1]
    if not es_id_valido(id_captura) or len(segmentos) != 4 or segmentos[2] != "original":
        raise ErrorPeticion("s3_key")
    if _RE_RESERVADO.fullmatch(segmentos[3]):
        raise ErrorPeticion("s3_key")
    return valor, id_captura


def _campo_texto(d: dict, campo: str, obligatorio: bool = False) -> str | None:
    valor = d.get(campo)
    if valor is None:
        if obligatorio:
            raise ErrorPeticion(campo)
        return None
    if not isinstance(valor, str) or _RE_CAMPO.fullmatch(valor) is None:
        raise ErrorPeticion(campo)
    return valor


def _campo_bool(d: dict, campo: str, por_defecto: bool) -> bool:
    if campo not in d or d[campo] is None:
        return por_defecto
    if type(d[campo]) is not bool:
        raise ErrorPeticion(campo)
    return d[campo]


def validar_peticion(d) -> dict:
    """Petición directa normalizada (sección 5.1 del diseño). No llama a la red."""
    if not isinstance(d, dict):
        raise ErrorPeticion("body")
    s3_key, id_de_clave = (None, None)
    if d.get("s3_key") is not None:
        s3_key, id_de_clave = validar_s3_key(d["s3_key"])
    id_pedido = d.get("id_captura")
    if id_pedido is not None and not es_id_valido(id_pedido):
        raise ErrorPeticion("id_captura")
    if s3_key is None and id_pedido is None:
        raise ErrorPeticion("id_captura")
    if id_de_clave and id_pedido and id_de_clave != id_pedido:
        raise ErrorPeticion("id_captura")
    fecha = None
    if d.get("fecha_observacion") is not None:
        fecha = validar_fecha(d["fecha_observacion"])
    modo = d.get("modo", "opencv")
    if modo is None:
        modo = "opencv"
    if modo not in MODOS:
        raise ErrorPeticion("modo")
    return {
        "s3_key": s3_key,
        "id_captura": id_de_clave or id_pedido,
        "id_nuevo": not (id_de_clave or id_pedido),
        "id_educadora": _campo_texto(d, "id_educadora"),
        "sala_grupo": _campo_texto(d, "sala_grupo"),
        "id_jardin": _campo_texto(d, "id_jardin"),
        "fecha_observacion": fecha,
        "modo": modo,
        "escribir_texto": _campo_bool(d, "escribir_texto", True),
        "incluir_urls": _campo_bool(d, "incluir_urls", False),
    }


# ----------------------------------------------------------------------------- meta.json

def armar_meta(id_educadora: str, sala_grupo: str, fecha: date) -> dict:
    meta = {"id_educadora": id_educadora, "sala_grupo": sala_grupo,
            "fecha_observacion": fecha.isoformat(), "tipo": "foto"}
    validar_meta_propio(meta)
    return meta


def validar_meta_propio(d: dict) -> None:
    """Lo que escribe esta Lambda: exactamente los 4 campos de Meta del equipo. ValueError(campo)."""
    if not isinstance(d, dict) or set(d) != {"id_educadora", "sala_grupo", "fecha_observacion", "tipo"}:
        raise ValueError("campos")
    for campo in ("id_educadora", "sala_grupo"):
        if not isinstance(d[campo], str) or _RE_CAMPO.fullmatch(d[campo]) is None:
            raise ValueError(campo)
    try:
        validar_fecha(d["fecha_observacion"])
    except ErrorPeticion:
        raise ValueError("fecha_observacion") from None
    if d["tipo"] != "foto":
        raise ValueError("tipo")


def leer_meta_existente(d) -> MetaLeida:
    """meta.json que ya estaba. Nunca más estricta que core.modelos.Meta (lanza MetaInvalida solo
    en casos que Meta también rechaza)."""
    if not isinstance(d, dict):
        raise MetaInvalida("meta")
    for campo in ("id_educadora", "sala_grupo"):
        if not isinstance(d.get(campo), str):
            raise MetaInvalida(campo)
    valor = d.get("fecha_observacion")
    if "fecha_observacion" not in d or valor is None or isinstance(valor, (bool, list, dict)):
        raise MetaInvalida("fecha_observacion")
    tipo = d.get("tipo")
    if tipo is not None and not isinstance(tipo, str):
        raise MetaInvalida("tipo")
    fecha = None
    if isinstance(valor, str):
        m = re.match(r"(\d{4}-\d{2}-\d{2})(?:$|[T ])", valor)
        if m:
            try:
                fecha = date.fromisoformat(m.group(1))
            except ValueError:
                fecha = None
    return MetaLeida(d["id_educadora"], d["sala_grupo"], fecha, fecha is None)


# ----------------------------------------------------------------------------- texto.json

def armar_texto(id_captura: str, partes: list[dict]) -> dict:
    """texto.json: una parte por post-it, con texto literal, archivo y legibilidad."""
    return {"id_captura": id_captura, "fuente": "ocr",
            "partes": [{"texto": p["texto"], "archivo": p["archivo"], "legibilidad": p["legibilidad"]}
                       for p in partes]}


def validar_texto(d: dict, id_captura: str, claves_disponibles: set[str]) -> None:
    """Espejo estricto de TextoCaptura: cada `archivo` apunta a una clave escrita en esta corrida o
    al origen `original/foto.jpg` ya presente. ValueError(campo)."""
    if not isinstance(d, dict) or d.get("id_captura") != id_captura or not es_id_valido(id_captura):
        raise ValueError("id_captura")
    if d.get("fuente") != "ocr":
        raise ValueError("fuente")
    partes = d.get("partes")
    if not isinstance(partes, list):
        raise ValueError("partes")
    for i, parte in enumerate(partes, start=1):
        if not isinstance(parte, dict):
            raise ValueError(f"partes[{i}]")
        if not isinstance(parte.get("texto"), str) or not parte["texto"].strip():
            raise ValueError(f"partes[{i}].texto")
        archivo = parte.get("archivo")
        if (not isinstance(archivo, str) or not archivo.startswith("original/")
                or clave(id_captura, archivo) not in claves_disponibles):
            raise ValueError(f"partes[{i}].archivo")
        if parte.get("legibilidad") not in LEGIBILIDADES:
            raise ValueError(f"partes[{i}].legibilidad")
