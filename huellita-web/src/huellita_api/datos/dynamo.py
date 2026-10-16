"""DynamoDB en crudo: entra y sale todo en formato AttributeValue (`{"S": "..."}`).

Este módulo no traduce nada (eso es `mapeo.py`) y no sabe de modelos ni de reglas: solo
paginación, lotes y las condiciones que no son errores.
"""
from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any

import boto3
from botocore.config import Config as ConfigBoto
from botocore.exceptions import ClientError

if TYPE_CHECKING:  # pragma: no cover - solo para los tipos
    from botocore.client import BaseClient

TAMANO_LOTE = 100
VUELTAS_LOTE = 3
FALLA_CONDICION = "ConditionalCheckFailedException"

AJUSTES_BOTO = ConfigBoto(
    connect_timeout=3,
    read_timeout=8,
    retries={"mode": "standard"},
)


@functools.cache
def cliente() -> BaseClient:
    """Cliente compartido de DynamoDB (3 s para conectar, 8 s para leer)."""
    return boto3.client("dynamodb", config=AJUSTES_BOTO)


def consultar_todo(tabla: str, **parametros: object) -> list[dict]:
    """`Query` paginado: sigue `LastEvaluatedKey` hasta el final.

    Acepta los parámetros de la API tal cual (`IndexName`, `KeyConditionExpression`,
    `ExpressionAttributeValues`, ...) y devuelve los ítems en el orden de DynamoDB.
    """
    items: list[dict] = []
    desde: dict | None = None
    while True:
        peticion: dict[str, Any] = {"TableName": tabla, **parametros}
        if desde:
            peticion["ExclusiveStartKey"] = desde
        respuesta = cliente().query(**peticion)
        items.extend(respuesta.get("Items", []))
        desde = respuesta.get("LastEvaluatedKey")
        if not desde:
            return items


def obtener(tabla: str, clave: dict) -> dict | None:
    """`GetItem`: el ítem o `None` si no está."""
    return cliente().get_item(TableName=tabla, Key=clave).get("Item")


def obtener_varios(tabla: str, claves: list[dict]) -> dict[str, dict]:
    """`BatchGetItem` en lotes de 100, reintentando las claves sin procesar.

    Devuelve `{valor de la primera clave: ítem}`; las claves que no existen no aparecen.
    """
    if not claves:
        return {}
    nombre = next(iter(claves[0]))
    encontrados: dict[str, dict] = {}
    for inicio in range(0, len(claves), TAMANO_LOTE):
        pendientes = claves[inicio : inicio + TAMANO_LOTE]
        for _ in range(VUELTAS_LOTE):
            if not pendientes:
                break
            respuesta = cliente().batch_get_item(RequestItems={tabla: {"Keys": pendientes}})
            for item in respuesta.get("Responses", {}).get(tabla, []):
                valor = next(iter(item[nombre].values()))
                encontrados[valor] = item
            pendientes = respuesta.get("UnprocessedKeys", {}).get(tabla, {}).get("Keys", [])
    return encontrados


def poner(tabla: str, item: dict, condicion: str | None = None) -> bool:
    """`PutItem`. Devuelve `False` (sin lanzar) si la condición no se cumple."""
    peticion: dict[str, Any] = {"TableName": tabla, "Item": item}
    if condicion:
        peticion["ConditionExpression"] = condicion
    try:
        cliente().put_item(**peticion)
    except ClientError as falla:
        if falla.response.get("Error", {}).get("Code") == FALLA_CONDICION:
            return False
        raise
    return True


def actualizar(
    tabla: str,
    clave: dict,
    expresion: str,
    valores: dict | None = None,
    condicion: str | None = None,
    nombres: dict[str, str] | None = None,
) -> dict | None:
    """`UpdateItem` con `ALL_NEW`. Devuelve `None` si la condición no se cumple."""
    peticion: dict[str, Any] = {
        "TableName": tabla,
        "Key": clave,
        "UpdateExpression": expresion,
        "ReturnValues": "ALL_NEW",
    }
    if valores:
        peticion["ExpressionAttributeValues"] = valores
    if condicion:
        peticion["ConditionExpression"] = condicion
    if nombres:
        peticion["ExpressionAttributeNames"] = nombres
    try:
        return cliente().update_item(**peticion).get("Attributes")
    except ClientError as falla:
        if falla.response.get("Error", {}).get("Code") == FALLA_CONDICION:
            return None
        raise


def borrar(tabla: str, clave: dict) -> None:
    """`DeleteItem`: borrar lo que no está no es un error."""
    cliente().delete_item(TableName=tabla, Key=clave)
