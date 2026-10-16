"""Prueba de punta a punta en AWS de postits-ocr con ProcesarNota (no va en el zip).

    python prueba_e2e.py --env RUTA\\.env --libro RUTA\\capturas_reales.json --evidencia RUTA\\e2e
        (--humo | --ensayo --foto RUTA | --real --foto RUTA | --seguir --foto RUTA)

- --humo: invoca con una captura sin foto (IMAGEN_NO_ENCONTRADA); no escribe nada.
- --ensayo: reserva un id CAP-<ULID> por foto (SHA-256) en el libro, sube los bytes tal cual a
  capturas/{id}/original/foto.jpg e invoca con escribir_texto=false (no escribe meta.json ni
  texto.json). Valida los documentos con los modelos del equipo, el listado de la carpeta, que
  Registros no tenga la captura y que los logs de la invocación no lleven textos ni nombres.
- --real: solo desde ensayo_ok y con el mismo código desplegado (CodeSha256). Invoca la MISMA
  petición del ensayo con escribir_texto=true, sondea Registros hasta PROCESADO/ERROR/SIN_TEXTO
  (cada 25 s, hasta 15 min), lee Observaciones y comprueba con head_object cada archivo_s3.
  Guarda Ninos de la sala antes y después, con las diferencias (no revierte nada).
- --seguir: retoma el sondeo de una captura real.

Como máximo 2 capturas reales en el libro. Las únicas escrituras desde el PC son put_object de
capturas/{id}/original/foto.jpg de ids del libro. Salidas: 0 bien; 1 falla; 2 regla del libro; 3 credenciales.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ.parent / "integra-backend" / "src"))

FUNCION = "postits-ocr"
MAXIMO_REALES = 2
GRUPO_LOGS = "/aws/lambda/postits-ocr"
AVISOS_OK = ("PLAN_B", "ESCRITURA_NO_CONDICIONAL", "TEMPERATURA_NO_SOPORTADA")
ESTADOS_PREVIOS = ("reservado", "foto_subida", "ensayo_ok", "ensayo_con_avisos", "ensayo_fallido")
FINALES = ("PROCESADO", "ERROR", "SIN_TEXTO")


def _ahora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, default=str)


class Libro:
    def __init__(self, ruta: Path):
        self.ruta = ruta
        self.datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.is_file() else {
            "version": 1, "maximo_reales": MAXIMO_REALES, "entradas": []}

    def guardar(self):
        tmp = self.ruta.with_suffix(".tmp")
        tmp.write_text(_json(self.datos), encoding="utf-8")
        os.replace(tmp, self.ruta)

    def entrada(self, sha: str):
        return next((e for e in self.datos["entradas"] if e["sha256"] == sha), None)

    def estado(self, e: dict, estado: str, detalle: str = ""):
        e["estado"] = estado
        e["eventos"].append({"t": _ahora(), "estado": estado, "detalle": detalle})
        self.guardar()

    def reales(self) -> int:
        return sum(1 for e in self.datos["entradas"] if e["estado"] not in ESTADOS_PREVIOS)


def _invocar(lam, peticion: dict) -> tuple[dict, str, float]:
    t = time.time()
    r = lam.invoke(FunctionName=FUNCION, InvocationType="RequestResponse", Payload=json.dumps(peticion).encode())
    cuerpo = json.loads(r["Payload"].read())
    if r.get("FunctionError"):
        cuerpo = {"error": {"codigo": "FUNCTION_ERROR", "mensaje": str(cuerpo)[:500]}}
    return cuerpo, r["ResponseMetadata"]["RequestId"], t


def _logs_de(logs, request_id: str, t_inicio: float) -> list[str]:
    """Líneas del log de la invocación (de START a REPORT). Vacío si el REPORT no aparece en 90 s."""
    for _ in range(45):
        eventos, token = [], None
        while True:
            kw = {"logGroupName": GRUPO_LOGS, "startTime": int((t_inicio - 60) * 1000)}
            if token:
                kw["nextToken"] = token
            r = logs.filter_log_events(**kw)
            eventos += r.get("events", [])
            token = r.get("nextToken")
            if not token:
                break
        mensajes = [e["message"] for e in sorted(eventos, key=lambda e: (e["timestamp"], e.get("ingestionTime", 0)))]
        if any(m.startswith(f"REPORT RequestId: {request_id}") for m in mensajes):
            inicio = next((i for i, m in enumerate(mensajes) if m.startswith(f"START RequestId: {request_id}")), 0)
            fin = next(i for i, m in enumerate(mensajes) if m.startswith(f"REPORT RequestId: {request_id}"))
            previas = [m for m in mensajes[:inicio] if '"evento": "inicio"' in m or "INIT_START" in m]
            return previas + mensajes[inicio:fin + 1]
        time.sleep(2)
    return []


def _revisar_privacidad(lineas: list[str], textos: list[str], nombres: list[str]) -> list[str]:
    hallazgos = []
    texto_log = "\n".join(lineas)
    for nombre in nombres:
        if re.search(rf"(?<!\w){re.escape(nombre)}(?!\w)", texto_log, re.IGNORECASE):
            hallazgos.append("nombre de la nomina en los logs")
    for texto in textos:
        for linea in texto.split("\n"):
            linea = linea.replace("[ilegible]", "").strip()
            if len(linea) >= 6 and linea.lower() in texto_log.lower():
                hallazgos.append("texto leido en los logs")
    return sorted(set(hallazgos))


def _nomina(tabla_ed, tabla_ninos, id_educadora: str, sala: str) -> tuple[str, list[dict]]:
    from boto3.dynamodb.conditions import Attr, Key

    jardin = tabla_ed.get_item(Key={"id_educadora": id_educadora})["Item"]["id_jardin"]
    items, kw = [], {"KeyConditionExpression": Key("id_jardin").eq(jardin), "FilterExpression": Attr("sala_grupo").eq(sala)}
    while True:
        r = tabla_ninos.query(**kw)
        items += r.get("Items", [])
        if not r.get("LastEvaluatedKey"):
            return jardin, items
        kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]


def _foto_ninos(items: list[dict]) -> dict:
    campos = ("ultima_obs_fecha", "ultimo_nivel", "ultimo_nivel_fecha")
    return {i["id_nino"]: {"nombre": i.get("nombre", ""), **{c: i.get(c) for c in campos}} for i in items}


def _nombres(items: list[dict]) -> list[str]:
    salida = set()
    for i in items:
        for n in [i.get("nombre", ""), *(i.get("apodos") or [])]:
            if isinstance(n, str) and len(n.strip()) >= 3:
                salida.add(n.strip())
    return sorted(salida)


def _validar_documentos(meta, texto) -> list[str]:
    from core.modelos import Meta, TextoCaptura

    errores = []
    try:
        if meta is not None:
            Meta.model_validate(meta)
    except Exception as e:
        errores.append(f"Meta: {type(e).__name__}")
    try:
        tc = TextoCaptura.model_validate(texto)
        if len(tc.partes_normalizadas()) != len(texto.get("partes", [])):
            errores.append("TextoCaptura: partes")
    except Exception as e:
        errores.append(f"TextoCaptura: {type(e).__name__}")
    return errores


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", required=True)
    parser.add_argument("--libro", required=True)
    parser.add_argument("--evidencia", required=True)
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument("--humo", action="store_true")
    modo.add_argument("--ensayo", action="store_true")
    modo.add_argument("--real", action="store_true")
    modo.add_argument("--seguir", action="store_true")
    parser.add_argument("--foto")
    parser.add_argument("--id-educadora", default="EDU-0001")
    parser.add_argument("--sala-grupo", default="SG-A")
    args = parser.parse_args()

    import entorno
    from botocore.config import Config

    sys.path.insert(0, str(RAIZ))
    import captura

    entorno.cargar_env(args.env)
    sesion = entorno.sesion_verificada()
    rec = entorno.recursos_equipo(sesion.client("cloudformation"))
    bucket = rec["bucket"]
    s3 = sesion.client("s3")
    lam = sesion.client("lambda", config=Config(read_timeout=90, connect_timeout=10, retries={"max_attempts": 0}))
    logs = sesion.client("logs")
    ddb = sesion.resource("dynamodb")
    t_reg, t_obs = ddb.Table(rec["registros"]), ddb.Table(rec["observaciones"])
    t_ninos, t_ed = ddb.Table(rec["ninos"]), ddb.Table(rec["educadoras"])
    libro = Libro(Path(args.libro))
    evid_raiz = Path(args.evidencia)

    if args.humo:
        peticion = {"id_captura": captura.nuevo_id_captura(), "id_educadora": args.id_educadora, "sala_grupo": args.sala_grupo}
        cuerpo, rid, t = _invocar(lam, peticion)
        print("humo:", _json(cuerpo))
        lineas = _logs_de(logs, rid, t)
        print("logs:", *[l.strip() for l in lineas], sep="\n  ")
        return 0 if cuerpo.get("error", {}).get("codigo") == "IMAGEN_NO_ENCONTRADA" else 1

    foto = Path(args.foto)
    datos = foto.read_bytes()
    sha = hashlib.sha256(datos).hexdigest()
    if datos[:3] != b"\xff\xd8\xff":
        print("la foto no es JPEG")
        return 2
    e = libro.entrada(sha)
    conf = lam.get_function_configuration(FunctionName=FUNCION)

    if args.ensayo:
        if e is None:
            if len(libro.datos["entradas"]) >= MAXIMO_REALES:
                print("el libro ya tiene 2 fotos")
                return 2
            id_captura = captura.nuevo_id_captura()
            e = {"foto": str(foto), "sha256": sha, "bytes": len(datos), "id_captura": id_captura,
                 "peticion": {"id_captura": id_captura, "id_educadora": args.id_educadora, "sala_grupo": args.sala_grupo,
                              "fecha_observacion": captura.hoy_chile().isoformat()},
                 "estado": "", "ensayos": 0, "reintentos_real": 0, "eventos": []}
            libro.datos["entradas"].append(e)
            libro.estado(e, "reservado")
        if e["estado"] not in ESTADOS_PREVIOS:
            print(f"la entrada esta en {e['estado']}: usa --seguir")
            return 2
        if e["ensayos"] >= 3:
            print("ya se hicieron 3 ensayos con esta foto")
            return 2
        id_captura = e["id_captura"]
        if not captura.es_id_valido(id_captura):
            return 2
        evid = evid_raiz / id_captura
        evid.mkdir(parents=True, exist_ok=True)
        clave_foto = captura.clave(id_captura, "original/foto.jpg")
        if re.fullmatch(r"capturas/CAP-[0-9A-HJKMNP-TV-Z]{26}/original/foto\.jpg", clave_foto) is None:
            return 2
        if e["estado"] == "reservado":
            s3.put_object(Bucket=bucket, Key=clave_foto, Body=datos, ContentType="image/jpeg")
            libro.estado(e, "foto_subida", clave_foto)
        e["ensayos"] += 1
        cuerpo, rid, t = _invocar(lam, {**e["peticion"], "escribir_texto": False})
        (evid / f"ensayo_{e['ensayos']}.json").write_text(_json(cuerpo), encoding="utf-8")
        problemas = []
        if "error" in cuerpo:
            libro.estado(e, "ensayo_fallido", cuerpo["error"]["codigo"])
            print("ensayo:", _json(cuerpo))
            return 1
        problemas += _validar_documentos(cuerpo["documentos"]["meta.json"], cuerpo["documentos"]["texto.json"])
        if cuerpo["n_postits"] < 1:
            problemas.append("sin post-its")
        listado = {o["Key"] for p in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=captura.prefijo(id_captura))
                   for o in p.get("Contents", [])}
        if any(k.endswith(".json") for k in listado):
            problemas.append("hay JSON en la carpeta")
        faltan = {captura.clave(id_captura, p["archivo"]) for p in cuerpo["partes"]} - listado
        if faltan:
            problemas.append(f"faltan {len(faltan)} objetos")
        if t_reg.get_item(Key={"id_captura": id_captura}).get("Item"):
            problemas.append("Registros ya tiene la captura")
        _, items = _nomina(t_ed, t_ninos, e["peticion"]["id_educadora"], e["peticion"]["sala_grupo"])
        lineas = _logs_de(logs, rid, t)
        if not lineas:
            problemas.append("LOGS_NO_DISPONIBLES")
        problemas += _revisar_privacidad(lineas, [p["texto"] for p in cuerpo["partes"]], _nombres(items))
        avisos = [a for a in cuerpo["avisos"] if not a.startswith(AVISOS_OK)]
        reporte = next((l for l in lineas if l.startswith("REPORT")), "")
        (evid / f"ensayo_{e['ensayos']}_revision.json").write_text(_json({
            "request_id": rid, "problemas": problemas, "avisos": cuerpo["avisos"], "listado": sorted(listado),
            "report": reporte.strip(), "lineas_log": len(lineas)}), encoding="utf-8")
        print("n_postits:", cuerpo["n_postits"], "modo:", cuerpo["modo"], "tiempos:", cuerpo["tiempos_ms"])
        for p in cuerpo["partes"]:
            print(f"  {p['orden']:02d} [{p['color']}/{p['legibilidad']}] {p['texto']!r}")
        print("avisos:", cuerpo["avisos"], "| problemas:", problemas)
        print("report:", reporte.strip())
        e["code_sha256_ensayo"] = conf["CodeSha256"]
        estado = "ensayo_ok" if not problemas and not avisos else ("ensayo_fallido" if problemas else "ensayo_con_avisos")
        libro.estado(e, estado, ";".join(problemas + avisos)[:300])
        return 0 if estado == "ensayo_ok" else 1

    if e is None:
        print("la foto no esta en el libro: haz primero --ensayo")
        return 2
    id_captura = e["id_captura"]
    evid = evid_raiz / id_captura
    evid.mkdir(parents=True, exist_ok=True)
    pref = captura.prefijo(id_captura)

    if args.real:
        listado = {o["Key"] for p in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=pref)
                   for o in p.get("Contents", [])}
        if e["estado"] == "ensayo_ok":
            pass
        elif e["estado"] == "real_fallido" and e["reintentos_real"] == 0 and captura.clave(id_captura, "texto.json") not in listado:
            e["reintentos_real"] = 1
        else:
            print(f"--real no se permite desde {e['estado']}")
            return 2
        if libro.reales() >= MAXIMO_REALES and e["estado"] == "ensayo_ok":
            print("ya hay 2 capturas reales")
            return 2
        if conf["CodeSha256"] != e.get("code_sha256_ensayo"):
            print("el codigo desplegado cambio desde el ensayo: repite el ensayo")
            return 2
        if libro.datos["entradas"][0]["sha256"] != sha and libro.datos["entradas"][0]["estado"] in ESTADOS_PREVIOS:
            print("la primera captura real tiene que ser la primera foto del libro")
            return 2
        jardin, items = _nomina(t_ed, t_ninos, e["peticion"]["id_educadora"], e["peticion"]["sala_grupo"])
        antes = _foto_ninos(items)
        (evid / "ninos_antes.json").write_text(_json(antes), encoding="utf-8")
        libro.estado(e, "real_invocado")
        cuerpo, rid, t = _invocar(lam, {**e["peticion"], "escribir_texto": True})
        t_fin = time.time()
        (evid / "real.json").write_text(_json(cuerpo), encoding="utf-8")
        if "error" in cuerpo or not cuerpo.get("texto_escrito"):
            libro.estado(e, "real_fallido", cuerpo.get("error", {}).get("codigo", "sin texto"))
            print("real:", _json(cuerpo))
            return 1
        meta = json.loads(s3.get_object(Bucket=bucket, Key=captura.clave(id_captura, "meta.json"))["Body"].read())
        texto = json.loads(s3.get_object(Bucket=bucket, Key=captura.clave(id_captura, "texto.json"))["Body"].read())
        errores = _validar_documentos(meta, texto)
        for p in texto["partes"]:
            s3.head_object(Bucket=bucket, Key=captura.clave(id_captura, p["archivo"]))
        print("real: meta_escrito", cuerpo["meta_escrito"], "texto_escrito", cuerpo["texto_escrito"],
              "avisos", cuerpo["avisos"], "validacion", errores or "OK", "tiempos", cuerpo["tiempos_ms"])
        lineas = _logs_de(logs, rid, t)
        e["real"] = {"request_id": rid, "t_texto_escrito": t_fin,
                     "report": next((l.strip() for l in lineas if l.startswith("REPORT")), ""),
                     "privacidad": _revisar_privacidad(lineas, [p["texto"] for p in cuerpo["partes"]], _nombres(items))}
        libro.estado(e, "real_escrito", ";".join(errores))

    if e["estado"] not in ("real_escrito", "real_invocado"):
        print(f"no hay nada que seguir desde {e['estado']}")
        return 2
    texto = json.loads(s3.get_object(Bucket=bucket, Key=captura.clave(id_captura, "texto.json"))["Body"].read())
    if e["estado"] == "real_invocado":
        libro.estado(e, "real_escrito", "retomado con --seguir")
    t_texto = e.get("real", {}).get("t_texto_escrito", time.time())
    vistos, registro = [], None
    limite = time.time() + 15 * 60
    while time.time() < limite:
        registro = t_reg.get_item(Key={"id_captura": id_captura}).get("Item")
        estado = (registro or {}).get("estado")
        if not vistos or vistos[-1][0] != estado:
            vistos.append((estado, round(time.time() - t_texto)))
            print(f"Registros.estado={estado} a los {vistos[-1][1]} s")
        if estado in FINALES:
            break
        time.sleep(25)
    (evid / "registro.json").write_text(_json({"registro": registro, "estados": vistos}), encoding="utf-8")
    if (registro or {}).get("estado") not in FINALES:
        print("Registros no llego a un estado final en 15 min: retoma con --seguir")
        return 1
    filas, kw = [], {"KeyConditionExpression": "id_captura = :i", "ExpressionAttributeValues": {":i": id_captura}}
    while True:
        r = t_obs.query(**kw)
        filas += r.get("Items", [])
        if not r.get("LastEvaluatedKey"):
            break
        kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]
    tabla, problemas = [], []
    for f in sorted(filas, key=lambda f: f["id_obs"]):
        m = re.fullmatch(rf"{re.escape(id_captura)}-p(\d+)-(\d+)", f["id_obs"])
        n = int(m.group(1)) if m else None
        esperado = captura.clave(id_captura, texto["partes"][n]["archivo"]) if n is not None and n < len(texto["partes"]) else None
        existe = True
        try:
            s3.head_object(Bucket=bucket, Key=f.get("archivo_s3", ""))
        except Exception:
            existe = False
        if not existe or f.get("archivo_s3") != esperado:
            problemas.append(f"{f['id_obs']}: archivo_s3 {'no existe' if not existe else 'distinto'}")
        tabla.append({k: f.get(k) for k in ("id_obs", "tipo", "id_nino", "error_identificacion", "evaluabilidad",
                                             "motivo_no_evaluable", "nivel", "certeza", "archivo_s3", "texto_literal")}
                     | {"parte": n, "archivo_s3_existe": existe})
    partes_con_obs = {t["parte"] for t in tabla}
    sin_obs = [i for i in range(len(texto["partes"])) if i not in partes_con_obs]
    _, items = _nomina(t_ed, t_ninos, e["peticion"]["id_educadora"], e["peticion"]["sala_grupo"])
    despues = _foto_ninos(items)
    antes = json.loads((evid / "ninos_antes.json").read_text(encoding="utf-8")) if (evid / "ninos_antes.json").is_file() else {}
    diferencias = [{"id_nino": k, "nombre": v["nombre"], "campo": c, "antes": antes.get(k, {}).get(c), "despues": v[c]}
                   for k, v in despues.items() for c in ("ultima_obs_fecha", "ultimo_nivel", "ultimo_nivel_fecha")
                   if str(antes.get(k, {}).get(c)) != str(v[c])]
    (evid / "observaciones.json").write_text(_json({"filas": tabla, "problemas": problemas, "partes_sin_obs": sin_obs,
                                                    "errores_registro": (registro or {}).get("errores")}), encoding="utf-8")
    (evid / "ninos_despues.json").write_text(_json(despues), encoding="utf-8")
    (evid / "ninos_diferencias.json").write_text(_json(diferencias), encoding="utf-8")
    print(f"Observaciones: {len(tabla)} filas; problemas: {problemas or 'ninguno'}; partes sin obs: {sin_obs}")
    for t in tabla:
        print(f"  {t['id_obs']} parte={t['parte']} tipo={t['tipo']} nino={t['id_nino']} err={t['error_identificacion']} "
              f"eval={t['evaluabilidad']} nivel={t['nivel']} archivo_s3={t['archivo_s3']} existe={t['archivo_s3_existe']}")
    print("Ninos cambiados:", _json(diferencias))
    libro.estado(e, "seguimiento_ok", f"{len(tabla)} observaciones; {len(problemas)} problemas")
    return 0 if not problemas else 1


if __name__ == "__main__":
    sys.exit(main())
