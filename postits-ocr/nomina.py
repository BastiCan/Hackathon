"""Nómina de la sala (solo lectura), como ayuda para leer la letra de los post-its.

    nomina.contexto(id_educadora, sala_grupo, fecha, id_jardin=None) -> Contexto

- NominaDynamo: GetItem en Educadoras (id_jardin) y Query en la tabla base Ninos por id_jardin,
  con filtro sala_grupo. Nunca escribe ni hace Scan.
- NominaLocal: el mismo contrato sobre integra-backend/tests/fixtures/nomina_demo.json.

La sala se considera conocida con el criterio de pipeline.procesar_nota: hay al menos un niño de la
sala con fecha_ingreso <= fecha, tenga o no nombre. Al prompt solo van los niños con nombre.
Los logs llevan solo códigos y conteos, nunca nombres.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

log = logging.getLogger("postits.nomina")

_RE_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass
class Contexto:
    id_jardin: str | None
    ninos: list[dict] = field(default_factory=list)
    estado: str = "ok"  # ok | educadora_desconocida | sala_desconocida | no_disponible
    detalle: str | None = None


class JardinNoCoincide(Exception):
    """La petición trae un id_jardin distinto del de la educadora."""


def fecha_ingreso_valida(item: dict) -> bool:
    valor = item.get("fecha_ingreso")
    return isinstance(valor, str) and _RE_FECHA.fullmatch(valor) is not None


def _armar(items: list[dict], id_jardin: str, fecha: date | None) -> Contexto:
    vigentes = [i for i in items
                if fecha is None or not fecha_ingreso_valida(i) or i["fecha_ingreso"] <= fecha.isoformat()]
    if not vigentes:
        return Contexto(id_jardin, [], "sala_desconocida")
    ninos = [{"nombre": i["nombre"].strip(), "apellido": "",
              "apodos": [a for a in (i.get("apodos") or []) if isinstance(a, str) and a.strip()]}
             for i in vigentes if isinstance(i.get("nombre"), str) and i["nombre"].strip()]
    ninos.sort(key=lambda n: n["nombre"].casefold())
    return Contexto(id_jardin, ninos, "ok")


class NominaDynamo:
    def __init__(self, tabla_educadoras: str, tabla_ninos: str, cliente=None):
        self.tabla_educadoras = tabla_educadoras
        self.tabla_ninos = tabla_ninos
        if cliente is None:
            import boto3
            from botocore.config import Config

            cliente = boto3.client("dynamodb", config=Config(retries={"mode": "standard", "max_attempts": 3},
                                                             connect_timeout=5, read_timeout=10))
        self.cliente = cliente

    def contexto(self, id_educadora: str, sala_grupo: str, fecha: date | None, id_jardin: str | None = None) -> Contexto:
        from boto3.dynamodb.types import TypeDeserializer
        from botocore.exceptions import ClientError

        des = TypeDeserializer()
        try:
            r = self.cliente.get_item(TableName=self.tabla_educadoras, Key={"id_educadora": {"S": id_educadora}},
                                      ProjectionExpression="#j", ExpressionAttributeNames={"#j": "id_jardin"})
            item = r.get("Item")
            jardin = des.deserialize(item["id_jardin"]) if item and "id_jardin" in item else None
            if not isinstance(jardin, str) or not jardin:
                log.info("nomina estado=educadora_desconocida")
                return Contexto(None, [], "educadora_desconocida")
            if id_jardin and id_jardin != jardin:
                raise JardinNoCoincide()
        except ClientError as e:
            codigo = e.response.get("Error", {}).get("Code", "ClientError")
            if not id_jardin:
                log.warning("nomina estado=no_disponible op=GetItem codigo=%s", codigo)
                return Contexto(None, [], "no_disponible", codigo)
            jardin = id_jardin
        items: list[dict] = []
        argumentos = {
            "TableName": self.tabla_ninos,
            "KeyConditionExpression": "#j = :j",
            "FilterExpression": "#s = :s",
            "ProjectionExpression": "#n, #a, #f",
            "ExpressionAttributeNames": {"#j": "id_jardin", "#s": "sala_grupo", "#n": "nombre", "#a": "apodos",
                                         "#f": "fecha_ingreso"},
            "ExpressionAttributeValues": {":j": {"S": jardin}, ":s": {"S": sala_grupo}},
        }
        try:
            while True:
                r = self.cliente.query(**argumentos)
                items.extend({k: des.deserialize(v) for k, v in i.items()} for i in r.get("Items", []))
                if not r.get("LastEvaluatedKey"):
                    break
                argumentos["ExclusiveStartKey"] = r["LastEvaluatedKey"]
        except ClientError as e:
            codigo = e.response.get("Error", {}).get("Code", "ClientError")
            log.warning("nomina estado=no_disponible op=Query codigo=%s", codigo)
            return Contexto(jardin, [], "no_disponible", codigo)
        ctx = _armar(items, jardin, fecha)
        log.info("nomina estado=%s items=%d con_nombre=%d", ctx.estado, len(items), len(ctx.ninos))
        return ctx


class NominaLocal:
    def __init__(self, ruta: str | Path | None = None):
        if ruta is None:
            ruta = os.environ.get("POSTITS_NOMINA_LOCAL") or (
                Path(__file__).resolve().parents[1] / "integra-backend" / "tests" / "fixtures" / "nomina_demo.json")
        self.ruta = Path(ruta)

    def contexto(self, id_educadora: str, sala_grupo: str, fecha: date | None, id_jardin: str | None = None) -> Contexto:
        if not self.ruta.is_file():
            return Contexto(id_jardin, [], "no_disponible", "SIN_ARCHIVO")
        datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        jardin = next((e.get("id_jardin") for e in datos.get("educadoras", [])
                       if e.get("id_educadora") == id_educadora), None)
        if not isinstance(jardin, str) or not jardin:
            return Contexto(None, [], "educadora_desconocida")
        if id_jardin and id_jardin != jardin:
            raise JardinNoCoincide()
        items = [n for n in datos.get("ninos", []) if n.get("id_jardin") == jardin and n.get("sala_grupo") == sala_grupo]
        return _armar(items, jardin, fecha)
