"""Arma el zip de la Lambda integra-ingesta y crea o actualiza el stack `integra-ingesta` con boto3.

    python ingesta\\desplegar.py --env RUTA\\.env [--tmp CARPETA] [--solo-zip]

1. Zip: ingesta.py, capturas_equipo.py (copia de integra-backend/src/core/capturas.py) y python-ulid
   (puro Python, pip --target). boto3 es el del runtime. El zip es determinista: mismo código, mismo sha.
2. Sesión verificada (cuenta 277702547089, us-east-1) con postits-ocr/entorno.py.
3. Sube el zip a s3://postits-ocr-despliegue-<cuenta>/ingesta/ingesta-<sha256[:16]>.zip.
4. create_stack o update_stack con template.yaml (SAM: CloudFormation aplica la transformación),
   CAPABILITY_IAM y CAPABILITY_AUTO_EXPAND, etiqueta proyecto=integra-ingesta. Imprime los outputs.

No toca el bucket de capturas, los stacks del equipo ni postits-ocr. No imprime credenciales ni claves.
Salidas: 0 bien; 1 falla; 2 bloqueante; 3 credenciales vencidas.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
EQUIPO = RAIZ.parent / "integra-backend" / "src" / "core" / "capturas.py"
STACK = "integra-ingesta"
ETIQUETA = {"Key": "proyecto", "Value": "integra-ingesta"}
ULID_VERSION = "4.0.1"  # la misma que postits-ocr


def armar_zip(tmp: Path) -> Path:
    paquete = tmp / "paquete"
    if paquete.exists():
        shutil.rmtree(paquete)
    paquete.mkdir(parents=True)
    subprocess.run([sys.executable, "-m", "pip", "install", f"python-ulid=={ULID_VERSION}", "--target", str(paquete),
                    "--no-cache-dir", "--no-deps", "--quiet", "--disable-pip-version-check"], check=True)
    shutil.copy2(RAIZ / "ingesta.py", paquete / "ingesta.py")
    shutil.copy2(EQUIPO, paquete / "capturas_equipo.py")
    destino = tmp / "ingesta_lambda.zip"
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(paquete.rglob("*")):
            rel = f.relative_to(paquete)
            if not f.is_file() or rel.parts[0] in ("bin", "Scripts") or "__pycache__" in rel.parts:
                continue
            info = zipfile.ZipInfo(rel.as_posix(), date_time=(2020, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, f.read_bytes())
    nombres = zipfile.ZipFile(destino).namelist()
    for requerido in ("ingesta.py", "capturas_equipo.py", "ulid/__init__.py"):
        if requerido not in nombres:
            raise RuntimeError(f"falta {requerido} en el zip")
    print(f"zip: {destino} ({destino.stat().st_size} bytes, {len(nombres)} archivos)")
    return destino


def eventos_fallidos(cfn) -> None:
    for ev in cfn.describe_stack_events(StackName=STACK).get("StackEvents", [])[:40]:
        if ev.get("ResourceStatus", "").endswith("FAILED"):
            print(f"  {ev['LogicalResourceId']}: {ev['ResourceStatus']} - {ev.get('ResourceStatusReason', '')}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", required=True)
    parser.add_argument("--tmp", default=str(RAIZ / "dist"))
    parser.add_argument("--solo-zip", action="store_true")
    args = parser.parse_args()

    zip_ruta = armar_zip(Path(args.tmp))
    if args.solo_zip:
        return 0

    sys.path.insert(0, str(RAIZ.parent / "postits-ocr"))
    import entorno
    from botocore.exceptions import ClientError, WaiterError

    entorno.cargar_env(args.env)
    sesion = entorno.sesion_verificada()
    cfn, s3 = sesion.client("cloudformation"), sesion.client("s3")
    bucket = f"postits-ocr-despliegue-{entorno.CUENTA}"
    entorno.exigir_bucket_propio(bucket)  # solo el bucket de despliegue que ya existe
    sha = hashlib.sha256(zip_ruta.read_bytes()).hexdigest()
    clave = f"ingesta/ingesta-{sha[:16]}.zip"
    s3.upload_file(str(zip_ruta), bucket, clave)
    print(f"zip subido: s3://{bucket}/{clave}")

    argumentos = {
        "StackName": STACK, "TemplateBody": (RAIZ / "template.yaml").read_text(encoding="utf-8"),
        "Parameters": [{"ParameterKey": "CodigoBucket", "ParameterValue": bucket},
                       {"ParameterKey": "CodigoClave", "ParameterValue": clave}],
        "Capabilities": ["CAPABILITY_IAM", "CAPABILITY_AUTO_EXPAND"], "Tags": [ETIQUETA],
    }
    try:
        estado = cfn.describe_stacks(StackName=STACK)["Stacks"][0]["StackStatus"]
    except ClientError as e:
        if "does not exist" not in str(e):
            raise
        estado = None
    print("estado previo del stack:", estado)
    espera = {"Delay": 10, "MaxAttempts": 60}
    try:
        if estado in (None, "DELETE_COMPLETE"):
            cfn.create_stack(OnFailure="ROLLBACK", **argumentos)
            cfn.get_waiter("stack_create_complete").wait(StackName=STACK, WaiterConfig=espera)
        elif estado in ("CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"):
            try:
                cfn.update_stack(**argumentos)
                cfn.get_waiter("stack_update_complete").wait(StackName=STACK, WaiterConfig=espera)
            except ClientError as e:
                if "No updates are to be performed" not in str(e):
                    raise
                print("sin cambios en el stack")
        else:
            print(f"el stack esta en {estado}: no se toca (si es ROLLBACK_COMPLETE, borrarlo y repetir)")
            eventos_fallidos(cfn)
            return 1
    except WaiterError:
        print("el stack no llego a COMPLETE; eventos fallidos:")
        eventos_fallidos(cfn)
        return 1
    pila = cfn.describe_stacks(StackName=STACK)["Stacks"][0]
    print("stack:", pila["StackStatus"])
    for o in pila.get("Outputs", []):
        print(f"  {o['OutputKey']}: {o['OutputValue']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
