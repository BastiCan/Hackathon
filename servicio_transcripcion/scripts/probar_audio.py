"""Prueba de humo: envía un audio local al transcriptor y consulta hasta que termine.

Uso en PowerShell:
  $env:TRANSCRIPTOR_URL = "https://<id>.execute-api.<region>.amazonaws.com/v1"   (por defecto http://127.0.0.1:8000)
  $env:TRANSCRIPTOR_API_KEY = "<valor de la clave>"                                 (no hace falta en local)
  python scripts/probar_audio.py "C:\ruta\nota.m4a" [id_captura]
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

URL = (os.environ.get("TRANSCRIPTOR_URL") or "http://127.0.0.1:8000").rstrip("/")


def pedir(metodo: str, ruta: str, cuerpo: dict | None = None) -> tuple[int, dict]:
    cabeceras = {"Content-Type": "application/json"}
    if os.environ.get("TRANSCRIPTOR_API_KEY"):
        cabeceras["x-api-key"] = os.environ["TRANSCRIPTOR_API_KEY"]
    datos = None if cuerpo is None else json.dumps(cuerpo).encode("utf-8")
    solicitud = urllib.request.Request(URL + ruta, data=datos, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(solicitud, timeout=30) as respuesta:
            return respuesta.status, json.loads(respuesta.read())
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except ValueError:
            return exc.code, {}
    except urllib.error.URLError as exc:
        raise SystemExit(f"No pude conectar con {URL} ({exc.reason}). ¿Está desplegado y cargaste TRANSCRIPTOR_URL?") from None


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ruta = sys.argv[1]
    if not os.path.isfile(ruta):
        print(f"No encuentro el archivo {ruta}. Pase la ruta completa entre comillas.")
        return 2
    print(f"Enviando {os.path.basename(ruta)} ({os.path.getsize(ruta) // 1024} KB) a {URL}")
    if not os.environ.get("TRANSCRIPTOR_API_KEY") and "execute-api" in URL:
        print("Aviso: falta TRANSCRIPTOR_API_KEY, así que API Gateway responderá 403.")
    id_captura = sys.argv[2] if len(sys.argv) > 2 else f"prueba-{int(time.time())}"
    with open(ruta, "rb") as archivo:
        audio = base64.b64encode(archivo.read()).decode("ascii")
    estado, cuerpo = pedir("POST", "/api/transcripciones/audio", {"id_captura": id_captura, "audio_base64": audio})
    print(estado, json.dumps(cuerpo, ensure_ascii=False, indent=2))
    if estado not in (200, 202):
        return 1
    limite = time.monotonic() + 180
    while cuerpo.get("estado") == "transcribiendo" and time.monotonic() < limite:
        time.sleep(3)
        estado, cuerpo = pedir("GET", f"/api/transcripciones/{cuerpo['id_trabajo']}")
    print(estado, json.dumps(cuerpo, ensure_ascii=False, indent=2))
    return 0 if cuerpo.get("estado") == "completado" else 1


if __name__ == "__main__":
    sys.exit(main())