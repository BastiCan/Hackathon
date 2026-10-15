"""Punto 4: _actualizar_nino no retrocede con observaciones en desorden (sin AWS).

Se usa una tabla Ninos falsa que simula el UpdateItem condicional de DynamoDB:
evalua la ConditionExpression (los dos casos que usa el codigo) contra un item en
memoria y lanza ConditionalCheckFailedException cuando no se cumple.
"""

from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from core.datos_aws import DatosDynamo
from core.modelos import Observacion, TipoObservacion

CLAVE = ("JAR-0001", "NIN-0001")


class _TablaNinosFake:
    """Simula AWS::DynamoDB Table.update_item con ConditionExpression (<= en fechas)."""

    def __init__(self) -> None:
        self.item: dict[str, Any] = {}

    def update_item(self, Key, UpdateExpression, ConditionExpression, ExpressionAttributeNames, ExpressionAttributeValues):
        nombres = ExpressionAttributeNames
        valores = ExpressionAttributeValues
        # Resolver la condicion: "attribute_not_exists(#x) OR #x <= :v".
        attr_alias = "#f" if "#f" in ConditionExpression else "#nf"
        val_alias = ":f" if ":f" in ConditionExpression else ":nf"
        campo = nombres[attr_alias]
        nuevo = valores[val_alias]
        actual = self.item.get(campo)
        if actual is not None and not (actual <= nuevo):
            raise ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException", "Message": "stale"}},
                "UpdateItem",
            )
        # Aplicar el SET (todos los pares del update).
        for alias, campo_real in nombres.items():
            # Mapear #f->:f, #n->:n, #nf->:nf por convencion.
            v_alias = ":" + alias[1:]
            if v_alias in valores:
                self.item[campo_real] = valores[v_alias]


def _datos_con_tabla_fake() -> tuple[DatosDynamo, _TablaNinosFake]:
    datos = object.__new__(DatosDynamo)  # evita __init__ (no toca AWS)
    tabla = _TablaNinosFake()
    datos._t_ninos = tabla
    return datos, tabla


def _obs(fecha: str, nivel: int | None) -> list[Observacion]:
    return [
        Observacion(
            id_obs=f"o-{fecha}",
            tipo=TipoObservacion.PARTICULAR,
            texto_literal="x",
            id_nino="NIN-0001",
            nivel=nivel,
        )
    ]


def _cab() -> dict:
    return {"id_jardin": "JAR-0001", "fecha": ""}  # fecha se setea por llamada


def test_fechas_en_desorden_no_retroceden() -> None:
    datos, tabla = _datos_con_tabla_fake()

    # Llega primero la mas nueva (2026-05-10, nivel 7).
    datos._actualizar_nino("JAR-0001", "NIN-0001", "2026-05-10", True, _obs("2026-05-10", 7))
    assert tabla.item["ultima_obs_fecha"] == "2026-05-10"
    assert tabla.item["ultimo_nivel"] == 7
    assert tabla.item["ultimo_nivel_fecha"] == "2026-05-10"

    # Llega una mas VIEJA (2026-01-01, nivel 3): no debe pisar nada.
    datos._actualizar_nino("JAR-0001", "NIN-0001", "2026-01-01", True, _obs("2026-01-01", 3))
    assert tabla.item["ultima_obs_fecha"] == "2026-05-10"
    assert tabla.item["ultimo_nivel"] == 7
    assert tabla.item["ultimo_nivel_fecha"] == "2026-05-10"

    # Llega una MAS NUEVA sin nivel (2026-09-01): avanza ultima_obs_fecha, no el nivel.
    datos._actualizar_nino("JAR-0001", "NIN-0001", "2026-09-01", False, _obs("2026-09-01", None))
    assert tabla.item["ultima_obs_fecha"] == "2026-09-01"
    assert tabla.item["ultimo_nivel"] == 7
    assert tabla.item["ultimo_nivel_fecha"] == "2026-05-10"

    # Llega una MAS NUEVA con nivel (2026-10-01, nivel 8): avanza todo.
    datos._actualizar_nino("JAR-0001", "NIN-0001", "2026-10-01", True, _obs("2026-10-01", 8))
    assert tabla.item["ultima_obs_fecha"] == "2026-10-01"
    assert tabla.item["ultimo_nivel"] == 8
    assert tabla.item["ultimo_nivel_fecha"] == "2026-10-01"
