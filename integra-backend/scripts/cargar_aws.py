r"""Carga los datos en AWS: Jardines/Educadoras/Ninos + historial, y la rubrica en S3.

- Jardines (20) desde data/raw/jardines.csv; `salas[]` = sala_grupo distintos del jardin
  deducidos de data/raw/ninos.csv.
- Educadoras (80) y Ninos (500) desde data/raw/*.csv. Donde exista (JAR-0001), superpone
  nombre/apodos de tests/fixtures/nomina_demo.json.
- Historial de observaciones (origen=dataset) en Observaciones: una por fila de
  data/raw/observaciones.csv, con sus manifestaciones (observacion_manifestaciones.csv +
  manifestaciones.csv). Por cada nino/a se calcula ultima_obs_fecha, ultimo_nivel y
  ultimo_nivel_fecha, que se escriben en Ninos.
- Sube a s3://<BUCKET>/rubrica/ : rubrica.json, fewshot.json, embeddings_rubrica.json.
  (Ya NO se sube data/raw/ al bucket: el dataset no vive en S3.)
- Imprime conteos.

Nota: el desafio menciona `consolidado.json` como fuente del historial; ese archivo no
esta en el repo (vivia en `datos_publicos/`). Su equivalente relacional son los CSV de
`data/raw/` (ver data/raw/README.md), que es lo que usa este script.

Lee los nombres de tabla/bucket del entorno (TABLA_*, BUCKET), que se setean tras el
deploy (p. ej. con scripts\cargar_env.ps1 o pegando los Outputs del stack en .env).

Uso (con credenciales y variables cargadas):
    .\.venv\Scripts\python.exe scripts\cargar_aws.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import boto3

from core.config import DATA_PROCESSED, DATA_RAW, config

NOMINA_DEMO = RAIZ / "tests" / "fixtures" / "nomina_demo.json"
ID_CAPTURA_DATASET = "DATASET"  # id_captura sintetico del historial precargado


# --- Lectura de CSV ---

def _leer_csv(nombre: str) -> list[dict[str, str]]:
    with (DATA_RAW / nombre).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _entero(valor: str | None) -> int | None:
    if valor is None or valor.strip() == "":
        return None
    try:
        return int(valor)
    except ValueError:
        return None


# --- Demo (nombres de JAR-0001) ---

def _demo_por_id() -> dict[str, dict]:
    with NOMINA_DEMO.open(encoding="utf-8") as f:
        demo = json.load(f)
    return {n["id_nino"]: n for n in demo.get("ninos", [])}


# --- Jardines ---

def _salas_por_jardin(ninos: list[dict[str, str]]) -> dict[str, list[str]]:
    """sala_grupo distintos por jardin (orden estable), deducidos de ninos.csv."""
    salas: dict[str, list[str]] = defaultdict(list)
    for fila in ninos:
        jar, sala = fila["id_jardin"], fila["sala_grupo"]
        if sala not in salas[jar]:
            salas[jar].append(sala)
    return {jar: sorted(lst) for jar, lst in salas.items()}


def _cargar_jardines(tabla, salas: dict[str, list[str]]) -> int:
    n = 0
    with tabla.batch_writer() as batch:
        for fila in _leer_csv("jardines.csv"):
            item = {
                "id_jardin": fila["id_jardin"],
                "nombre_fantasia": fila.get("nombre_fantasia", ""),
                "comuna": fila.get("comuna", ""),
                "region": fila.get("region", ""),
                "salas": salas.get(fila["id_jardin"], []),
            }
            if (v := _entero(fila.get("numero_salas"))) is not None:
                item["numero_salas"] = v
            if (v := _entero(fila.get("numero_educadoras"))) is not None:
                item["numero_educadoras"] = v
            batch.put_item(Item=item)
            n += 1
    return n


# --- Educadoras ---

def _cargar_educadoras(tabla) -> int:
    n = 0
    with tabla.batch_writer() as batch:
        for fila in _leer_csv("educadoras.csv"):
            batch.put_item(
                Item={
                    "id_educadora": fila["id_educadora"],
                    "id_jardin": fila["id_jardin"],
                    "rol": fila.get("rol", ""),
                }
            )
            n += 1
    return n


# --- Historial de observaciones (para texto_literal, nivel y agregados por nino) ---

def _manifestaciones_cruce() -> dict[str, dict[str, str]]:
    """id_manifestacion -> {nivel, dominio, texto_observable}."""
    cruce: dict[str, dict[str, str]] = {}
    for fila in _leer_csv("manifestaciones.csv"):
        cruce[fila["id_manifestacion"]] = {
            "nivel": fila["nivel"],
            "dominio": fila["dominio"],
            "texto_observable": fila["texto_observable"],
        }
    return cruce


def _manifestaciones_por_obs() -> dict[str, list[str]]:
    """id_observacion -> [id_manifestacion, ...] (orden del CSV)."""
    por_obs: dict[str, list[str]] = defaultdict(list)
    for fila in _leer_csv("observacion_manifestaciones.csv"):
        por_obs[fila["id_observacion"]].append(fila["id_manifestacion"])
    return por_obs


def _texto_de_observacion(mans: list[str], nota_breve: str, cruce: dict[str, dict[str, str]]) -> str:
    """texto_observable de cada manifestacion + nota_breve (misma receta que fewshot)."""
    partes = [cruce[m]["texto_observable"] for m in mans if m in cruce]
    if nota_breve and nota_breve.strip():
        partes.append(nota_breve.strip())
    return " ".join(partes)


def _cargar_historial(tabla, ninos_idx: dict[str, dict[str, str]]) -> tuple[int, dict[str, dict]]:
    """Escribe Observaciones (origen=dataset) y devuelve (conteo, agregados por nino).

    agregados[id_nino] = {ultima_obs_fecha, ultimo_nivel, ultimo_nivel_fecha}
    """
    cruce = _manifestaciones_cruce()
    por_obs = _manifestaciones_por_obs()
    agregados: dict[str, dict] = {}
    n = 0
    with tabla.batch_writer() as batch:
        for fila in _leer_csv("observaciones.csv"):
            id_obs = fila["id_observacion"]
            id_nino = fila["id_nino"]
            fecha = fila["fecha_observacion"]
            nivel = _entero(fila.get("nivel_estimado"))
            nino = ninos_idx.get(id_nino, {})
            id_jardin = nino.get("id_jardin", "")
            sala_grupo = nino.get("sala_grupo", "")
            mans = por_obs.get(id_obs, [])
            texto = _texto_de_observacion(mans, fila.get("nota_breve", ""), cruce)

            item = {
                "id_captura": ID_CAPTURA_DATASET,
                "id_obs": id_obs,
                "origen": "dataset",
                "tipo": "PARTICULAR",
                "estado": "SUGERIDO",
                "id_nino": id_nino,
                "id_educadora": fila.get("id_educadora", ""),
                "id_jardin": id_jardin,
                "sala_grupo": sala_grupo,
                "sala_key": f"{id_jardin}#{sala_grupo}",
                "fecha": fecha,
                # orden = fecha#creado_en#tiebreak. Se usa medianoche -03:00 como creado_en
                # sintetico para que, dentro de un mismo dia, el historial (dataset) quede
                # ANTES que lo nuevo (orden = fecha#creado_en con hora real). id_obs desempata.
                "orden": f"{fecha}#{fecha}T00:00:00-03:00#{id_obs}",
                "texto_literal": texto,
                "manifestaciones": [
                    {
                        "id_manifestacion": m,
                        "nivel": _entero(cruce[m]["nivel"]),
                        "dominio": cruce[m]["dominio"],
                        "texto_observable": cruce[m]["texto_observable"],
                    }
                    for m in mans
                    if m in cruce
                ],
            }
            if nivel is not None:
                item["nivel"] = nivel
            batch.put_item(Item=item)
            n += 1
            _actualizar_agregado(agregados, id_nino, fecha, nivel)
    return n, agregados


def _actualizar_agregado(agregados: dict[str, dict], id_nino: str, fecha: str, nivel: int | None) -> None:
    """Mantiene por nino la ultima obs (max fecha) y el ultimo nivel conocido (max fecha con nivel)."""
    a = agregados.setdefault(id_nino, {})
    if fecha > a.get("ultima_obs_fecha", ""):
        a["ultima_obs_fecha"] = fecha
    if nivel is not None and fecha >= a.get("ultimo_nivel_fecha", ""):
        a["ultimo_nivel"] = nivel
        a["ultimo_nivel_fecha"] = fecha


# --- Ninos (con nombres de demo y agregados del historial) ---

def _cargar_ninos(tabla, demo: dict[str, dict], agregados: dict[str, dict]) -> int:
    n = 0
    with tabla.batch_writer() as batch:
        for fila in _leer_csv("ninos.csv"):
            item = {
                "id_nino": fila["id_nino"],
                "id_jardin": fila["id_jardin"],
                "sala_grupo": fila["sala_grupo"],
                "fecha_nacimiento": fila["fecha_nacimiento"],
                "fecha_ingreso": fila["fecha_ingreso"],
            }
            d = demo.get(fila["id_nino"])
            if d:
                item["nombre"] = d["nombre"]
                item["apodos"] = d.get("apodos", [])
            else:
                item["nombre"] = ""
                item["apodos"] = []
            # Agregados del historial (si el nino/a tiene observaciones).
            a = agregados.get(fila["id_nino"])
            if a:
                if a.get("ultima_obs_fecha"):
                    item["ultima_obs_fecha"] = a["ultima_obs_fecha"]
                if a.get("ultimo_nivel") is not None:
                    item["ultimo_nivel"] = a["ultimo_nivel"]
                    item["ultimo_nivel_fecha"] = a["ultimo_nivel_fecha"]
            batch.put_item(Item=item)
            n += 1
    return n


# --- S3 (solo rubrica/) ---

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


def main() -> int:
    if config.es_local:
        print("FUENTE_DATOS=local: este script es para AWS. Setea FUENTE_DATOS=aws y las TABLA_*/BUCKET.", file=sys.stderr)
        return 1
    faltan = [
        k
        for k, v in {
            "TABLA_JARDINES": config.tabla_jardines,
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

    ninos_csv = _leer_csv("ninos.csv")
    ninos_idx = {fila["id_nino"]: fila for fila in ninos_csv}
    demo = _demo_por_id()

    print("Cargando Jardines...")
    n_jar = _cargar_jardines(ddb.Table(config.tabla_jardines), _salas_por_jardin(ninos_csv))
    print(f"  Jardines: {n_jar}")

    print("Cargando Educadoras...")
    n_edu = _cargar_educadoras(ddb.Table(config.tabla_educadoras))
    print(f"  Educadoras: {n_edu}")

    print("Cargando historial de Observaciones (origen=dataset)...")
    n_obs, agregados = _cargar_historial(ddb.Table(config.tabla_observaciones), ninos_idx)
    print(f"  Observaciones: {n_obs} (ninos con historial: {len(agregados)})")

    print("Cargando Ninos...")
    n_ninos = _cargar_ninos(ddb.Table(config.tabla_ninos), demo, agregados)
    print(f"  Ninos: {n_ninos} (con nombre de demo: {len(demo)})")

    print("Subiendo rubrica/ a S3...")
    _subir_s3(s3, config.bucket)
    print("Listo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
