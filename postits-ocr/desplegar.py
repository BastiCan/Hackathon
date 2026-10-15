"""Despliega la Lambda postits-ocr con boto3 (stack CloudFormation propio `postits-ocr`). No va en el zip.

    python desplegar.py --env RUTA\\.env --zip RUTA\\postits_ocr_lambda.zip [--solo-verificar]

1. Sesión verificada (cuenta 277702547089, us-east-1) y recursos del stack del equipo (solo lectura).
2. Revisa (solo get) que ninguna notificación del bucket del equipo calce con los .jpg que escribe
   la Lambda, ni mande meta.json/texto.json a otra función que ProcesarNota. Si calza: salida 2.
3. Bucket de despliegue postits-ocr-despliegue-<cuenta> (privado, Block Public Access, SSE-S3,
   etiqueta proyecto=postits-ocr): se crea si no existe. Es el único bucket que se toca.
4. Sube el zip a lambda/postits-ocr-<sha256[:16]>.zip y crea o actualiza el stack con
   infra/plantilla.json (CAPABILITY_IAM). Si falla, imprime los eventos *_FAILED.

Nunca cambia la configuración del bucket del equipo, su stack, sus tablas ni otras Lambdas.
Salidas: 0 bien; 1 falla; 2 bloqueante; 3 credenciales vencidas o inválidas.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
STACK = "postits-ocr"
FUNCION = "postits-ocr"
ETIQUETA = {"Key": "proyecto", "Value": "postits-ocr"}
EJEMPLOS = ("original/foto.jpg", "original/postit_01.jpg", "original/overlay.jpg", "meta.json", "texto.json")


def _calza(config: dict, clave: str) -> bool:
    if not any(e.startswith("s3:ObjectCreated:") for e in config.get("Events", [])):
        return False
    reglas = {r["Name"].lower(): r["Value"] for r in config.get("Filter", {}).get("Key", {}).get("FilterRules", [])}
    return clave.startswith(reglas.get("prefix", "")) and clave.endswith(reglas.get("suffix", ""))


def revisar_notificaciones(s3, bucket: str, funcion_equipo: str) -> list[str]:
    """Bloqueantes de la configuración de notificaciones del bucket del equipo (solo lectura)."""
    conf = s3.get_bucket_notification_configuration(Bucket=bucket)
    bloqueantes = []
    claves = [f"capturas/CAP-01ARZ3NDEKTSV4RRFFQ69G5FAV/{r}" for r in EJEMPLOS]
    for tipo, campo_destino in (("LambdaFunctionConfigurations", "LambdaFunctionArn"),
                                ("QueueConfigurations", "QueueArn"), ("TopicConfigurations", "TopicArn")):
        for c in conf.get(tipo, []):
            destino = c.get(campo_destino, "")
            es_equipo = tipo == "LambdaFunctionConfigurations" and destino.split(":function:")[-1].split(":")[0] == funcion_equipo
            for clave in claves:
                if not _calza(c, clave):
                    continue
                if clave.endswith(".jpg"):
                    bloqueantes.append(f"{tipo} {destino} calza con {clave.rsplit('/', 1)[-1]}")
                elif not es_equipo:
                    bloqueantes.append(f"{tipo} {destino} calza con {clave.rsplit('/', 1)[-1]}")
            print(f"notificacion {tipo}: destino={destino.split(':')[-1]} eventos={c.get('Events')} "
                  f"filtros={c.get('Filter', {}).get('Key', {}).get('FilterRules', [])}")
    if "EventBridgeConfiguration" in conf:
        bloqueantes.append("el bucket envia eventos a EventBridge: revisar reglas a mano")
    return bloqueantes


def arns_bedrock(sesion, modelo: str, cuenta: str) -> tuple[str, list[str]]:
    try:
        perfil = sesion.client("bedrock").get_inference_profile(inferenceProfileIdentifier=modelo)
        arn = perfil["inferenceProfileArn"]
        base = [m["modelArn"] for m in perfil.get("models", [])]
        if base:
            return arn, base
    except Exception as e:  # sin permiso: ARN construidos
        print(f"aviso: get_inference_profile no disponible ({type(e).__name__}); ARN construidos")
    sin_prefijo = modelo.split(".", 1)[1] if modelo.startswith(("us.", "global.")) else modelo
    return (f"arn:aws:bedrock:us-east-1:{cuenta}:inference-profile/{modelo}",
            [f"arn:aws:bedrock:*::foundation-model/{sin_prefijo}"])


def bucket_despliegue(s3, nombre: str, entorno) -> None:
    from botocore.exceptions import ClientError

    entorno.exigir_bucket_propio(nombre)
    try:
        s3.head_bucket(Bucket=nombre)
        propios = {b["Name"] for b in s3.list_buckets().get("Buckets", [])}
        if nombre not in propios:
            raise entorno.Bloqueante("el bucket de despliegue existe y es de otro dueno")
        print(f"bucket de despliegue ya existe: {nombre}")
    except ClientError as e:
        codigo = e.response.get("Error", {}).get("Code", "")
        if codigo not in ("404", "NoSuchBucket", "NotFound"):
            raise entorno.Bloqueante(f"head_bucket del bucket de despliegue: {codigo}") from None
        s3.create_bucket(Bucket=nombre)
        print(f"bucket de despliegue creado: {nombre}")
    s3.get_waiter("bucket_exists").wait(Bucket=nombre)
    for nombre_op, llamada in (
            ("put_public_access_block", lambda: s3.put_public_access_block(Bucket=nombre, PublicAccessBlockConfiguration={
                "BlockPublicAcls": True, "IgnorePublicAcls": True, "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True})),
            ("put_bucket_encryption", lambda: s3.put_bucket_encryption(Bucket=nombre, ServerSideEncryptionConfiguration={
                "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]})),
            ("put_bucket_tagging", lambda: s3.put_bucket_tagging(Bucket=nombre, Tagging={"TagSet": [ETIQUETA]}))):
        entorno.exigir_bucket_propio(nombre)
        try:
            llamada()
        except ClientError as e:
            print(f"aviso: {nombre_op} -> {e.response.get('Error', {}).get('Code')}")


def eventos_fallidos(cfn) -> None:
    for ev in cfn.describe_stack_events(StackName=STACK).get("StackEvents", [])[:40]:
        if ev.get("ResourceStatus", "").endswith("FAILED"):
            print(f"  {ev['LogicalResourceId']}: {ev['ResourceStatus']} - {ev.get('ResourceStatusReason', '')}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", required=True)
    parser.add_argument("--zip", required=False)
    parser.add_argument("--solo-verificar", action="store_true")
    args = parser.parse_args()

    import os

    import entorno
    from botocore.exceptions import ClientError, WaiterError

    entorno.cargar_env(args.env)
    sesion = entorno.sesion_verificada()
    cuenta = entorno.CUENTA
    cfn, s3 = sesion.client("cloudformation"), sesion.client("s3")
    try:
        rec = entorno.recursos_equipo(cfn)
        print("recursos del equipo:", json.dumps(rec))
        bloqueantes = revisar_notificaciones(s3, rec["bucket"], rec["funcion"])
        if bloqueantes:
            print("BLOQUEANTES:", *bloqueantes, sep="\n  ")
            return 2
        modelo = os.environ.get("BEDROCK_MODEL_ID") or "us.anthropic.claude-haiku-4-5-20251001-v1:0"
        perfil, base = arns_bedrock(sesion, modelo, cuenta)
        print("perfil:", perfil, "modelos base:", base)
        if args.solo_verificar:
            return 0
        zip_ruta = Path(args.zip)
        sha = hashlib.sha256(zip_ruta.read_bytes()).hexdigest()
        bucket = f"postits-ocr-despliegue-{cuenta}"
        bucket_despliegue(s3, bucket, entorno)
        clave = f"lambda/postits-ocr-{sha[:16]}.zip"
        entorno.exigir_bucket_propio(bucket)
        t = time.time()
        s3.upload_file(str(zip_ruta), bucket, clave)
        print(f"zip subido: s3://{bucket}/{clave} ({zip_ruta.stat().st_size / 1048576:.1f} MiB, {time.time() - t:.0f} s)")
        parametros = {
            "NombreBucketCapturas": rec["bucket"], "TablaNinosNombre": rec["ninos"],
            "TablaEducadorasNombre": rec["educadoras"], "ModeloId": modelo, "PerfilInferenciaArn": perfil,
            "ModelosBaseArns": ",".join(base), "CodigoBucket": bucket, "CodigoClave": clave,
        }
        argumentos = {
            "StackName": STACK, "TemplateBody": (RAIZ / "infra" / "plantilla.json").read_text(encoding="utf-8"),
            "Parameters": [{"ParameterKey": k, "ParameterValue": v} for k, v in parametros.items()],
            "Capabilities": ["CAPABILITY_IAM"], "Tags": [ETIQUETA],
        }
        try:
            estado = cfn.describe_stacks(StackName=STACK)["Stacks"][0]["StackStatus"]
        except ClientError as e:
            if "does not exist" not in str(e):
                raise
            estado = None
        print("estado previo del stack:", estado)
        try:
            if estado in (None, "DELETE_COMPLETE"):
                cfn.create_stack(OnFailure="ROLLBACK", **argumentos)
                cfn.get_waiter("stack_create_complete").wait(StackName=STACK, WaiterConfig={"Delay": 10, "MaxAttempts": 60})
            elif estado in ("CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"):
                try:
                    cfn.update_stack(**argumentos)
                    cfn.get_waiter("stack_update_complete").wait(StackName=STACK,
                                                                 WaiterConfig={"Delay": 10, "MaxAttempts": 60})
                except ClientError as e:
                    if "No updates are to be performed" not in str(e):
                        raise
                    print("sin cambios en el stack")
            else:
                print(f"el stack esta en {estado}: no se toca")
                eventos_fallidos(cfn)
                return 1
        except WaiterError:
            print("el stack no llego a COMPLETE; eventos fallidos:")
            eventos_fallidos(cfn)
            return 1
        pila = cfn.describe_stacks(StackName=STACK)["Stacks"][0]
        print("stack:", pila["StackStatus"], pila["StackId"])
        for o in pila.get("Outputs", []):
            print(f"  {o['OutputKey']}: {o['OutputValue']}")
        lam = sesion.client("lambda")
        lam.get_waiter("function_active_v2").wait(FunctionName=FUNCION)
        lam.get_waiter("function_updated_v2").wait(FunctionName=FUNCION)
        conf = lam.get_function_configuration(FunctionName=FUNCION)
        print("funcion:", conf["State"], conf["LastUpdateStatus"], conf["CodeSha256"], conf["CodeSize"])
        conc = lam.get_function_concurrency(FunctionName=FUNCION).get("ReservedConcurrentExecutions")
        print("concurrencia reservada:", conc)
        if conc == 0:
            print("BLOQUEANTE: concurrencia reservada en 0")
            return 2
        return 0
    except entorno.Bloqueante as e:
        print("BLOQUEANTE:", e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
