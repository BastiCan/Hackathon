r"""Carga los datos en AWS: Educadoras y Ninos en DynamoDB, rubrica/ y raw/ en S3.

- Educadoras (80) y Ninos (500) desde data/raw/*.csv.
- Donde exista (JAR-0001), superpone nombre/apodos de tests/fixtures/nomina_demo.json.
- Sube a s3://<BUCKET>/rubrica/ : rubrica.json, fewshot.json, embeddings_rubrica.json.
- Sube data/raw/ a s3://<BUCKET>/raw/ (respaldo del dataset).
- Imprime conteos.

Lee los nombres de tabla/bucket del entorno (TABLA_*, BUCKET), que se setean tras el
deploy (p. ej. con scripts\cargar_env.ps1 o pegando los Outputs del stack en .env).

Uso (con credenciales y variables cargadas):
    .\.venv\Scripts\python.exe scripts\cargar_aws.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import boto3

from core.config import DATA_PROCESSED, DATA_RAW, config

NOMINA_DEMO = RAIZ / "tests" / "fixtures" / "nomina_demo.json"


def _demo_por_id() -> dict[str, dict]:
    with NOMINA_DEMO.open(encoding="utf-8") as f:
        demo = json.load(f)
    return {n["id_nino"]: n for n in demo.get("ninos", [])}


def _cargar_educadoras(tabla) -> int:
    n = 0
    with (DATA_RAW / "educadoras.csv").open(encoding="utf-8", newline="") as f, tabla.batch_writer() as batch:
        for fila in csv.DictReader(f):
            batch.put_item(
                Item={
                    "id_educadora": fila["id_educadora"],
                    "id_jardin": fila["id_jardin"],
                    "rol": fila.get("rol", ""),
                }
            )
            n += 1
    return n


def _cargar_ninos(tabla, demo: dict[str, dict]) -> int:
    n = 0
    with (DATA_RAW / "ninos.csv").open(encoding="utf-8", newline="") as f, tabla.batch_writer() as batch:
        for fila in csv.DictReader(f):
            item = {
                "id_nino": fila["id_nino"],
                "id_jardin": fila["id_jardin"],
                "sala_grupo": fila["sala_grupo"],
                "fecha_nacimiento": fila["fecha_nacimiento"],
                "fecha_ingreso": fila["fecha_ingreso"],
            }
            # Superponer nombre/apodos de demo donde exista (JAR-0001).
            d = demo.get(fila["id_nino"])
            if d:
                item["nombre"] = d["nombre"]
                item["apodos"] = d.get("apodos", [])
            else:
                # Sin nombre de demo: no se identifica por nombre en esta etapa.
                item["nombre"] = ""
                item["apodos"] = []
            batch.put_item(Item=item)
            n += 1
    return n


def _subir_s3(s3, bucket: str) -> None:
    for nombre, clave in [
        ("rubrica.json", "rubrica/rubrica.json"),
        ("fewshot.json", "rubrica/fewshot.json"),
        ("embeddings_rubrica.json", "rubrica/embeddings_rubrica.json"),
    ]:
        ruta = DATA_PROCESSED / nombre
        if not ruta.is_file():
            print(f"  AVISO: falta {ruta}, se omite", file=sys.stderr)
            continue
        s3.upload_file(str(ruta), bucket, clave)
        print(f"  subido {clave}")

    for ruta in sorted(DATA_RAW.glob("*")):
        if ruta.is_file():
            s3.upload_file(str(ruta), bucket, f"raw/{ruta.name}")
    print(f"  subido raw/ ({sum(1 for p in DATA_RAW.glob('*') if p.is_file())} archivos)")


def main() -> int:
    if config.es_local:
        print("FUENTE_DATOS=local: este script es para AWS. Setea FUENTE_DATOS=aws y las TABLA_*/BUCKET.", file=sys.stderr)
        return 1
    faltan = [
        k
        for k, v in {
            "TABLA_EDUCADORAS": config.tabla_educadoras,
            "TABLA_NINOS": config.tabla_ninos,
            "TABLA_OBSERVACIONES": config.tabla_observaciones,
            "BUCKET": config.bucket,
        }.items()
        if not v
    ]
    if faltan:
        print(f"ERROR: faltan variables de entorno: {', '.join(faltan)}", file=sys.stderr)
        return 1

    ddb = boto3.resource("dynamodb", region_name=config.region)
    s3 = boto3.client("s3", region_name=config.region)

    demo = _demo_por_id()
    print("Cargando Educadoras...")
    n_edu = _cargar_educadoras(ddb.Table(config.tabla_educadoras))
    print(f"  Educadoras: {n_edu}")
    print("Cargando Ninos...")
    n_ninos = _cargar_ninos(ddb.Table(config.tabla_ninos), demo)
    print(f"  Ninos: {n_ninos} (con nombre de demo: {len(demo)})")
    print("Subiendo a S3...")
    _subir_s3(s3, config.bucket)
    print("Listo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
