r"""Sube una captura de prueba a S3 para disparar el flujo (sin OCR).

Genera un id_captura CAP-<ULID>, sube `meta.json` y `texto.json` bajo
`capturas/<id>/` en el bucket de capturas (BUCKET_CAPTURAS). La notificacion S3
del template dispara la Lambda, que escribe Registros y Observaciones.

El `texto.json` por defecto es una nota escrita por la tia (sin archivo). Se puede
pasar texto propio con --texto; educadora/sala/fecha con --educadora/--sala/--fecha.

Uso (con credenciales y variables cargadas):
    .\.venv\Scripts\python.exe scripts\subir_captura_prueba.py
    .\.venv\Scripts\python.exe scripts\subir_captura_prueba.py --texto "Pedro apilo tres bloques" --sala SG-A
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import boto3
from ulid import ULID

from core.config import config

TEXTO_DEFECTO = "Pedro apilo tres bloques y despues conto 'uno, dos, tres' senalando cada uno."


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sube una captura de prueba a S3.")
    p.add_argument("--texto", default=TEXTO_DEFECTO, help="Texto de la nota (una parte, sin archivo).")
    p.add_argument("--educadora", default="EDU-0001", help="id_educadora (de meta.json).")
    p.add_argument("--sala", default="SG-A", help="sala_grupo (de meta.json).")
    p.add_argument("--fecha", default="2026-10-15", help="fecha_observacion ISO (de meta.json).")
    p.add_argument("--tipo", default="manual", help="tipo de nota (informativo).")
    return p.parse_args()


def main() -> int:
    if config.es_local:
        print("FUENTE_DATOS=local: este script sube a S3. Setea FUENTE_DATOS=aws.", file=sys.stderr)
        return 1
    if not config.bucket_capturas:
        print("ERROR: falta BUCKET_CAPTURAS en el entorno.", file=sys.stderr)
        return 1

    args = _parse_args()
    id_captura = f"CAP-{ULID()}"
    prefijo = f"capturas/{id_captura}"

    meta = {
        "id_educadora": args.educadora,
        "sala_grupo": args.sala,
        "fecha_observacion": args.fecha,
        "tipo": args.tipo,
    }
    texto = {
        "id_captura": id_captura,
        "fuente": "manual",
        "partes": [{"texto": args.texto}],
    }

    s3 = boto3.client("s3", region_name=config.region)
    bucket = config.bucket_capturas

    # Subir meta.json primero y texto.json despues (el upsert tolera cualquier orden).
    s3.put_object(
        Bucket=bucket,
        Key=f"{prefijo}/meta.json",
        Body=json.dumps(meta, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )
    print(f"  subido s3://{bucket}/{prefijo}/meta.json")
    s3.put_object(
        Bucket=bucket,
        Key=f"{prefijo}/texto.json",
        Body=json.dumps(texto, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )
    print(f"  subido s3://{bucket}/{prefijo}/texto.json")
    print(f"id_captura: {id_captura}")
    print("La Lambda deberia procesarlo. Revisa Registros (RECIBIDO->PROCESADO) y Observaciones.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
