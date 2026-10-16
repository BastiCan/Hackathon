"""Entorno local para desplegar.py y prueba_e2e.py (no va en el zip de la Lambda).

- cargar_env(ruta): lee CLAVE=valor y pone en os.environ solo las claves de CLAVES. Corta cada línea
  en el PRIMER "=" (los tokens de sesión traen "=", "/" y "+"). Nunca imprime valores.
- sesion_verificada(): STS; credenciales vencidas -> SystemExit(3); otra cuenta/región -> SystemExit(2).
- recursos_equipo(cfn, cuenta): nombres físicos desde los outputs del stack integra-procesador.
- exigir_bucket_propio(nombre, cuenta): el único bucket que se crea o configura es el de despliegue.
"""

from __future__ import annotations

import os
from pathlib import Path

CUENTA = "277702547089"
REGION = "us-east-1"
CLAVES = ("AWS_REGION", "AWS_DEFAULT_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
          "BEDROCK_MODEL_ID")
SALIDAS = {"bucket": "NombreBucketCapturas", "educadoras": "TablaEducadorasNombre", "ninos": "TablaNinosNombre",
           "registros": "TablaRegistrosNombre", "observaciones": "TablaObservacionesNombre", "funcion": "NombreFuncion"}


class Bloqueante(RuntimeError):
    pass


def cargar_env(ruta: str | Path | None = None, *, texto: str | None = None) -> list[str]:
    if texto is None:
        texto = Path(ruta).read_text(encoding="utf-8-sig")
    cargadas = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        if linea.startswith("export "):
            linea = linea[len("export "):].lstrip()
        clave, sep, valor = linea.partition("=")  # solo el primer "="
        if not sep:
            continue
        clave, valor = clave.strip(), valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
            valor = valor[1:-1]
        if clave in CLAVES:
            os.environ[clave] = valor
            cargadas.append(clave)
    for perfil in ("AWS_PROFILE", "AWS_DEFAULT_PROFILE"):
        os.environ.pop(perfil, None)
    print("claves cargadas:", ", ".join(sorted(set(cargadas))))
    return cargadas


def sesion_verificada(cuenta: str = CUENTA, region: str = REGION):
    import boto3
    from botocore.exceptions import ClientError

    for variable in ("AWS_REGION", "AWS_DEFAULT_REGION"):
        if os.environ.get(variable) and os.environ[variable] != region:
            print(f"{variable} no es {region}")
            raise SystemExit(2)
    sesion = boto3.Session(region_name=region)
    try:
        identidad = sesion.client("sts").get_caller_identity()
    except ClientError as e:
        codigo = e.response.get("Error", {}).get("Code", "")
        if codigo in ("ExpiredToken", "ExpiredTokenException", "InvalidClientTokenId", "UnrecognizedClientException"):
            print(f"credenciales vencidas o invalidas ({codigo})")
            raise SystemExit(3)
        raise
    if identidad["Account"] != cuenta:
        print("la sesion no es de la cuenta esperada")
        raise SystemExit(2)
    print("sesion:", identidad["Arn"].split("/")[-2] if "/" in identidad["Arn"] else identidad["Arn"])
    return sesion


def recursos_equipo(cfn, cuenta: str = CUENTA) -> dict[str, str]:
    pila = cfn.describe_stacks(StackName="integra-procesador")["Stacks"][0]
    if pila["StackStatus"] not in ("CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"):
        raise Bloqueante(f"integra-procesador en {pila['StackStatus']}")
    salidas = {o["OutputKey"]: o["OutputValue"] for o in pila.get("Outputs", [])}
    faltan = [c for c in SALIDAS.values() if not salidas.get(c)]
    if faltan:
        raise Bloqueante(f"faltan outputs de integra-procesador: {faltan}")
    recursos = {nombre: salidas[c] for nombre, c in SALIDAS.items()}
    if recursos["bucket"] != f"integra-capturas-{cuenta}":
        raise Bloqueante("el bucket de capturas no es integra-capturas-<cuenta>")
    return recursos


def exigir_bucket_propio(nombre: str, cuenta: str = CUENTA) -> None:
    if nombre != f"postits-ocr-despliegue-{cuenta}":
        raise RuntimeError("solo se crea o configura el bucket de despliegue de postits-ocr")
