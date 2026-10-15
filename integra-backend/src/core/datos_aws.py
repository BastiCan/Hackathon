"""Implementacion DynamoDB de la interfaz Datos (tarea 8).

Tablas (design.md):
- Educadoras: PK id_educadora
- Ninos: PK id_jardin, SK id_nino
- Observaciones: PK id_captura, SK id_obs

Mismo contrato que DatosLocal, para que el pipeline no sepa de donde salen los datos.
No se escribe el texto de las notas en logs (requirements 5): aqui solo se persiste.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import boto3

from .config import config
from .modelos import Educadora, Nino, Observacion


def _a_item_dynamo(valor: Any) -> Any:
    """Convierte un valor Python a algo que DynamoDB acepta.

    - float -> Decimal (DynamoDB no acepta float).
    - date/datetime -> isoformat.
    - dict/list -> recursivo; se omiten los None (DynamoDB no guarda null comodo).
    """
    if isinstance(valor, float):
        return Decimal(str(valor))
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {k: _a_item_dynamo(v) for k, v in valor.items() if v is not None}
    if isinstance(valor, list):
        return [_a_item_dynamo(v) for v in valor]
    return valor


def _observacion_a_item(obs: Observacion, id_captura: str, cabecera: dict[str, Any]) -> dict[str, Any]:
    """Serializa una Observacion a un item de la tabla Observaciones.

    `cabecera` trae los datos de captura comunes (fecha, id_educadora, id_jardin, etc.).
    """
    cuerpo = json.loads(obs.model_dump_json(exclude_none=True))
    item = {
        "id_captura": id_captura,
        "id_obs": obs.id_obs,
        "creado_en": datetime.now(UTC).isoformat(),
        **cabecera,
        **cuerpo,
    }
    return _a_item_dynamo(item)


class DatosDynamo:
    """Acceso a datos sobre DynamoDB."""

    def __init__(self) -> None:
        if not (config.tabla_educadoras and config.tabla_ninos and config.tabla_observaciones):
            raise ValueError("faltan TABLA_EDUCADORAS / TABLA_NINOS / TABLA_OBSERVACIONES en el entorno")
        self._ddb = boto3.resource("dynamodb", region_name=config.region)
        self._t_educadoras = self._ddb.Table(config.tabla_educadoras)
        self._t_ninos = self._ddb.Table(config.tabla_ninos)
        self._t_observaciones = self._ddb.Table(config.tabla_observaciones)

    def educadora(self, id_educadora: str) -> Educadora | None:
        resp = self._t_educadoras.get_item(Key={"id_educadora": id_educadora})
        item = resp.get("Item")
        if not item:
            return None
        return Educadora(
            id_educadora=item["id_educadora"],
            id_jardin=item["id_jardin"],
            rol=item.get("rol"),
        )

    def ninos_de_jardin(self, id_jardin: str) -> list[Nino]:
        from boto3.dynamodb.conditions import Key

        ninos: list[Nino] = []
        kwargs: dict[str, Any] = {"KeyConditionExpression": Key("id_jardin").eq(id_jardin)}
        while True:
            resp = self._t_ninos.query(**kwargs)
            for item in resp.get("Items", []):
                ninos.append(
                    Nino(
                        id_nino=item["id_nino"],
                        id_jardin=item["id_jardin"],
                        sala_grupo=item["sala_grupo"],
                        nombre=item["nombre"],
                        apodos=list(item.get("apodos", [])),
                        fecha_nacimiento=date.fromisoformat(item["fecha_nacimiento"]),
                        fecha_ingreso=date.fromisoformat(item["fecha_ingreso"]),
                    )
                )
            if "LastEvaluatedKey" not in resp:
                break
            kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
        return ninos

    def guardar_observaciones(
        self, observaciones: list[Observacion], id_captura: str = "", cabecera: dict[str, Any] | None = None
    ) -> None:
        cab = cabecera or {}
        with self._t_observaciones.batch_writer() as batch:
            for obs in observaciones:
                batch.put_item(Item=_observacion_a_item(obs, id_captura, cab))
