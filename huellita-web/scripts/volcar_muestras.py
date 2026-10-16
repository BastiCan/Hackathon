"""Vuelca muestras reales (datos ficticios del dataset E-1) de las tablas de integra-procesador.

Solo lectura: DescribeStacks, GetItem y Query. Escribe los ítems tal como los entrega
DynamoDB (formato AttributeValue) en tests/fixtures/, para probar mapeo.py con datos reales.

Uso en PowerShell, desde huellita-web (si el perfil usa `aws login`, boto3 necesita las
credenciales temporales en variables de entorno):
  aws configure export-credentials --profile hackaton --format powershell | Out-String | Invoke-Expression
  .\\.venv\\Scripts\\python.exe scripts\\volcar_muestras.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3

STACK = "integra-procesador"
JARDIN = "JAR-0001"
SALAS = ("SG-A", "SG-B")
DESTINO = Path(__file__).resolve().parents[1] / "tests" / "fixtures"


def _consultar_todo(cliente, **parametros) -> list[dict]:
    items: list[dict] = []
    while True:
        respuesta = cliente.query(**parametros)
        items.extend(respuesta.get("Items", []))
        siguiente = respuesta.get("LastEvaluatedKey")
        if not siguiente:
            return items
        parametros["ExclusiveStartKey"] = siguiente


def _guardar(nombre: str, contenido: object) -> None:
    ruta = DESTINO / nombre
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{ruta.name}: {len(contenido) if isinstance(contenido, list) else 1}")


def main() -> None:
    argumentos = argparse.ArgumentParser(description=__doc__)
    argumentos.add_argument("--profile", default=None, help="Perfil de AWS; por omisión, las variables de entorno")
    argumentos.add_argument("--region", default="us-east-1")
    opciones = argumentos.parse_args()

    sesion = boto3.Session(profile_name=opciones.profile, region_name=opciones.region)
    salidas = {
        o["OutputKey"]: o["OutputValue"]
        for o in sesion.client("cloudformation").describe_stacks(StackName=STACK)["Stacks"][0]["Outputs"]
    }
    ddb = sesion.client("dynamodb")
    DESTINO.mkdir(parents=True, exist_ok=True)

    jardin = ddb.get_item(TableName=salidas["TablaJardinesNombre"], Key={"id_jardin": {"S": JARDIN}})
    _guardar("jardin.json", jardin["Item"])
    _guardar(
        "educadoras.json",
        _consultar_todo(
            ddb,
            TableName=salidas["TablaEducadorasNombre"],
            IndexName="porJardin",
            KeyConditionExpression="id_jardin = :j",
            ExpressionAttributeValues={":j": {"S": JARDIN}},
        ),
    )
    _guardar(
        "ninos.json",
        _consultar_todo(
            ddb,
            TableName=salidas["TablaNinosNombre"],
            KeyConditionExpression="id_jardin = :j",
            ExpressionAttributeValues={":j": {"S": JARDIN}},
        ),
    )
    for sala in SALAS:
        clave = {":s": {"S": f"{JARDIN}#{sala}"}}
        sufijo = sala.lower().replace("-", "")
        _guardar(
            f"observaciones_{sufijo}.json",
            _consultar_todo(
                ddb,
                TableName=salidas["TablaObservacionesNombre"],
                IndexName="porSala",
                KeyConditionExpression="sala_key = :s",
                ExpressionAttributeValues=clave,
            ),
        )
        _guardar(
            f"registros_{sufijo}.json",
            _consultar_todo(
                ddb,
                TableName=salidas["TablaRegistrosNombre"],
                IndexName="porSala",
                KeyConditionExpression="sala_key = :s",
                ExpressionAttributeValues=clave,
            ),
        )


if __name__ == "__main__":
    main()
