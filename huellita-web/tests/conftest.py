"""Piezas comunes de las pruebas: fixtures reales del dataset, doble de DynamoDB y
rellenos de los módulos que escriben otros carriles (solo mientras no existan).

Ninguna prueba toca AWS: `dynamo.cliente` queda reemplazado por `ClienteFalso`.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_FIXTURES = Path(__file__).resolve().parent / "fixtures"
SEMILLA = RAIZ.parent / "huellita-formato-mejorado" / "data" / "semilla.json"
USUARIAS_DEMO = RAIZ / "src" / "huellita_api" / "datos" / "usuarias_demo.json"

FECHA_DEMO = "2026-10-15"
MOMENTO_DEMO = datetime.fromisoformat(f"{FECHA_DEMO}T15:00:00-03:00")

ENTORNO_PRUEBA: dict[str, str] = {
    "TABLA_JARDINES": "Jardines",
    "TABLA_EDUCADORAS": "Educadoras",
    "TABLA_NINOS": "Ninos",
    "TABLA_REGISTROS": "Registros",
    "TABLA_OBSERVACIONES": "Observaciones",
    "TABLA_CAPTURAS": "Capturas",
    "TABLA_DECISIONES": "Decisiones",
    "BUCKET_CAPTURAS": "integra-capturas-000000000000",
    "URL_TRANSCRIPTOR": "https://transcriptor.invalido/v1",
    "ID_CLAVE_TRANSCRIPTOR": "clave-de-prueba",
    "JARDIN_DEMO": "JAR-0001",
    "SALAS_DEMO": "SG-A,SG-B",
    "MAX_CAPTURAS_DIA": "2",
    "MINUTOS_MAX_PROCESANDO": "20",
    "ZONA_HORARIA": "America/Santiago",
}


# --- rellenos de otros carriles --------------------------------------------------------


def _falta(nombre: str) -> bool:
    try:
        return importlib.util.find_spec(nombre) is None
    except (ImportError, ValueError):
        return True


def _registrar(nombre: str, modulo: ModuleType) -> None:
    sys.modules[nombre] = modulo
    paquete, _, hoja = nombre.rpartition(".")
    setattr(importlib.import_module(paquete), hoja, modulo)


def _relleno_auth() -> ModuleType:
    """`auth.usuarias()` según el contrato, mientras el carril de la app no publique el suyo."""
    from huellita_api.modelos import Usuaria

    modulo = ModuleType("huellita_api.auth")
    modulo.CABECERA_USUARIA = "X-Usuaria-Id"
    modulo.usuarias = lambda: [
        Usuaria(**u) for u in json.loads(USUARIAS_DEMO.read_text(encoding="utf-8"))["usuarias"]
    ]
    return modulo


def _relleno_decisiones() -> ModuleType:
    """`leer_por_sala` y `aplicar` (regla 7) según el contrato, para poder leer registros."""
    from huellita_api import mapeo
    from huellita_api.datos import dynamo
    from huellita_api.modelos import Original, Sugerencia

    modulo = ModuleType("huellita_api.datos.decisiones")

    def leer_por_sala(cfg: Any, sala_key: str) -> dict[str, dict]:
        items = dynamo.consultar_todo(
            cfg.tabla_decisiones,
            KeyConditionExpression="sala_key = :sk",
            ExpressionAttributeValues={":sk": {"S": sala_key}},
        )
        planos = [{clave: mapeo.desanidar(valor) for clave, valor in item.items()} for item in items]
        return {str(plano.get("id_sugerencia")): plano for plano in planos}

    def aplicar(sugerencia: Sugerencia, decision: dict) -> Sugerencia:
        if decision.get("estado") not in ("aceptada", "cambiada", "descartada"):
            return sugerencia
        mapa = decision.get("original")
        cambios: dict[str, Any] = {
            "estado": decision.get("estado"),
            "validadaPor": decision.get("validada_por"),
            "validadaEn": decision.get("validada_en"),
            "original": Original(
                ninoId=mapa.get("nino_id"), nucleo=mapa.get("nucleo"), nivel=mapa.get("nivel")
            )
            if isinstance(mapa, dict)
            else None,
        }
        for campo, clave in (("ninoId", "nino_id"), ("nucleo", "nucleo"), ("nivel", "nivel")):
            if decision.get(clave) is not None:
                cambios[campo] = decision[clave]
        return sugerencia.model_copy(update=cambios)

    modulo.leer_por_sala = leer_por_sala
    modulo.aplicar = aplicar
    return modulo


if _falta("huellita_api.auth"):
    _registrar("huellita_api.auth", _relleno_auth())
if _falta("huellita_api.datos.decisiones"):
    _registrar("huellita_api.datos.decisiones", _relleno_decisiones())


# --- doble de DynamoDB -----------------------------------------------------------------


class ClienteFalso:
    """Doble del cliente de DynamoDB: AttributeValue puro, sin red.

    Soporta lo que usa el carril de lectura: `query` (con paginación), `get_item`,
    `batch_get_item` (con claves sin procesar) y `update_item` con expresiones `SET`.
    Guarda cada llamada para poder afirmar sobre ellas.
    """

    def __init__(
        self,
        tablas: dict[str, list[dict]] | None = None,
        *,
        tam_pagina: int = 50,
        sin_procesar: int = 0,
    ) -> None:
        self.tablas = {nombre: list(items) for nombre, items in (tablas or {}).items()}
        self.tam_pagina = tam_pagina
        self.sin_procesar = sin_procesar
        self.consultas: list[dict] = []
        self.claves_pedidas: list[str] = []
        self.actualizaciones: list[dict] = []

    # -- lecturas
    def query(self, **peticion: Any) -> dict:
        self.consultas.append(peticion)
        tabla = peticion["TableName"]
        atributo, marcador = (parte.strip() for parte in peticion["KeyConditionExpression"].split("="))
        esperado = peticion["ExpressionAttributeValues"][marcador]
        # Un ítem sin el atributo de la clave no está en el índice: así son los dispersos.
        items = [item for item in self.tablas.get(tabla, []) if item.get(atributo) == esperado]
        desde = int(peticion.get("ExclusiveStartKey", {}).get("_pos", {}).get("N", "0"))
        respuesta: dict[str, Any] = {"Items": items[desde : desde + self.tam_pagina]}
        if desde + self.tam_pagina < len(items):
            respuesta["LastEvaluatedKey"] = {"_pos": {"N": str(desde + self.tam_pagina)}}
        return respuesta

    def get_item(self, TableName: str, Key: dict) -> dict:  # noqa: N803 - nombres de la API
        item = self._buscar(TableName, Key)
        return {"Item": item} if item is not None else {}

    def batch_get_item(self, RequestItems: dict) -> dict:  # noqa: N803 - nombres de la API
        ((tabla, peticion),) = RequestItems.items()
        claves = list(peticion["Keys"])
        for clave in claves:
            self.claves_pedidas.append(str(next(iter(clave.values())).get("S", "")))
        aplazadas, claves = claves[: self.sin_procesar], claves[self.sin_procesar :]
        self.sin_procesar = 0
        items = [item for clave in claves if (item := self._buscar(tabla, clave)) is not None]
        respuesta: dict[str, Any] = {"Responses": {tabla: items}, "UnprocessedKeys": {}}
        if aplazadas:
            respuesta["UnprocessedKeys"] = {tabla: {"Keys": aplazadas}}
        return respuesta

    # -- escrituras
    def update_item(self, **peticion: Any) -> dict:
        self.actualizaciones.append(peticion)
        tabla, clave = peticion["TableName"], peticion["Key"]
        valores = peticion.get("ExpressionAttributeValues", {})
        item = self._buscar(tabla, clave)
        if item is None:
            item = dict(clave)
            self.tablas.setdefault(tabla, []).append(item)
        expresion = peticion["UpdateExpression"]
        if expresion.upper().startswith("SET "):
            for asignacion in expresion[4:].split(","):
                nombre, _, marcador = asignacion.partition("=")
                item[nombre.strip()] = valores[marcador.strip()]
        return {"Attributes": item}

    def _buscar(self, tabla: str, clave: dict) -> dict | None:
        for item in self.tablas.get(tabla, []):
            if all(item.get(nombre) == valor for nombre, valor in clave.items()):
                return item
        return None


# --- fixtures --------------------------------------------------------------------------


def leer_fixture(nombre: str) -> Any:
    """Un volcado real de DynamoDB de `tests/fixtures`."""
    return json.loads((CARPETA_FIXTURES / f"{nombre}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def fixtures() -> dict[str, Any]:
    nombres = (
        "jardin",
        "educadoras",
        "ninos",
        "observaciones_sga",
        "observaciones_sgb",
        "registros_sga",
        "registros_sgb",
    )
    return {nombre: leer_fixture(nombre) for nombre in nombres}


@pytest.fixture(scope="session")
def semilla() -> dict[str, Any]:
    """La semilla del modo local: la referencia de las reglas 1, 2 y 4."""
    return json.loads(SEMILLA.read_text(encoding="utf-8"))


@pytest.fixture
def cfg():
    from huellita_api.config import cargar_config

    return cargar_config(ENTORNO_PRUEBA)


@pytest.fixture
def reloj_demo():
    """Reloj inyectado: las 15:00 del día de la demo, en Chile."""
    return lambda: MOMENTO_DEMO


@pytest.fixture
def dynamo_falso(monkeypatch: pytest.MonkeyPatch):
    """Instala el doble de DynamoDB y lo devuelve para poder revisar las llamadas."""
    from huellita_api.datos import dynamo

    def instalar(tablas: dict[str, list[dict]] | None = None, **opciones: Any) -> ClienteFalso:
        cliente = ClienteFalso(tablas, **opciones)
        monkeypatch.setattr(dynamo, "cliente", lambda: cliente)
        return cliente

    return instalar
