r"""Mide la calidad de la clasificacion sobre tests/fixtures/validacion_100.json.

Protagonista CONOCIDO: mide solo conductas + clasificacion (no identifica por nombre).
Usa SOLO el campo `nota` (lo que escribiria una tia). `texto_control` (texto literal de
la rubrica) solo se usa con --depurar y NUNCA se reporta como resultado (Requirement 10).

Metricas (Requirement 10.2):
- accuracy de codigo (conjunto exacto), recall y precision de codigos
- accuracy de nivel (exacto y +/-1)
- accuracy de dominio
- accuracy por nivel de certeza (alta/media/baja)

Salidas: data/eval/reporte.md (agregado) y data/eval/resultados.jsonl (detalle por caso).

Uso:
    .\.venv\Scripts\python.exe scripts\medir.py
    .\.venv\Scripts\python.exe scripts\medir.py --max 20          # subconjunto rapido
    .\.venv\Scripts\python.exe scripts\medir.py --depurar         # usa texto_control (debug)
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from core.config import FEWSHOT_LOCAL
from core.datos import DatosLocal
from core.pipeline import clasificar_texto, construir_contexto
from core.retriever import Retriever
from core.rubrica import cargar_rubrica

VALIDACION = RAIZ / "tests" / "fixtures" / "validacion_100.json"
EVAL_DIR = RAIZ / "data" / "eval"


def _evaluar_caso(ctx, caso, depurar: bool) -> dict:
    texto = caso["texto_control"] if depurar else caso["nota"]
    protagonista = caso.get("protagonista", "")
    esperado = caso["esperado"]
    cod_esperados = set(esperado["manifestaciones"])
    try:
        res = clasificar_texto(ctx, texto, protagonista)
        cod_obtenidos = {s.id_manifestacion for s in res.sugerencias}
        niveles_obt = {s.nivel for s in res.sugerencias}
        dominios_obt = {s.dominio for s in res.sugerencias}
        return {
            "id_caso": caso["id_caso"],
            "evaluable": res.evaluable,
            "codigos_esperados": sorted(cod_esperados),
            "codigos_obtenidos": sorted(cod_obtenidos),
            "nivel_esperado": esperado["nivel"],
            "nivel_obtenido": res.nivel,
            "dominios_esperados": esperado["dominios"],
            "dominios_obtenidos": sorted(dominios_obt),
            "niveles_obtenidos": sorted(n for n in niveles_obt if n is not None),
            "certeza": res.certeza.value if res.certeza else None,
            "error": None,
        }
    except Exception as e:  # noqa: BLE001 - un caso que falla no detiene la medicion
        return {
            "id_caso": caso["id_caso"],
            "error": f"{type(e).__name__}: {e}",
            "codigos_esperados": sorted(cod_esperados),
            "nivel_esperado": esperado["nivel"],
            "dominios_esperados": esperado["dominios"],
        }


def _metricas(resultados: list[dict]) -> dict:
    validos = [r for r in resultados if not r.get("error")]
    n = len(validos)
    if n == 0:
        return {"n": 0}

    cod_exacto = 0
    recall_num = recall_den = prec_num = prec_den = 0
    nivel_exacto = nivel_pm1 = 0
    dom_ok = 0
    por_certeza: dict[str, list[int]] = {"alta": [], "media": [], "baja": [], "sin": []}

    for r in validos:
        esp = set(r["codigos_esperados"])
        obt = set(r["codigos_obtenidos"])
        if esp == obt:
            cod_exacto += 1
        recall_num += len(esp & obt)
        recall_den += len(esp)
        prec_num += len(esp & obt)
        prec_den += len(obt)

        # Nivel: se compara el nivel esperado con los niveles de los codigos obtenidos.
        ne = r["nivel_esperado"]
        niveles_obt = r["niveles_obtenidos"]
        acerto_nivel = ne in niveles_obt
        acerto_pm1 = any(abs(ne - no) <= 1 for no in niveles_obt)
        nivel_exacto += 1 if acerto_nivel else 0
        nivel_pm1 += 1 if acerto_pm1 else 0

        # Dominio: esperados incluidos en obtenidos.
        if set(r["dominios_esperados"]) <= set(r["dominios_obtenidos"]):
            dom_ok += 1

        cert = r.get("certeza") or "sin"
        por_certeza.setdefault(cert, [])
        por_certeza[cert].append(1 if acerto_nivel else 0)

    def pct(a, b):
        return round(100.0 * a / b, 1) if b else 0.0

    acc_certeza = {
        c: {"n": len(v), "acc_nivel": pct(sum(v), len(v))}
        for c, v in por_certeza.items()
        if v
    }

    # Matriz de confusion de NIVEL: esperado (fila) x nivel principal obtenido (columna).
    # El nivel obtenido es el consolidado principal (obs.nivel); None (sin codigo) -> "0".
    matriz: dict[int, dict[int, int]] = {}
    for r in validos:
        ne = r["nivel_esperado"]
        no = r.get("nivel_obtenido")
        col = no if no is not None else 0  # 0 = sin codigo / no evaluable
        matriz.setdefault(ne, {})
        matriz[ne][col] = matriz[ne].get(col, 0) + 1

    # Confusiones de CODIGO: una matriz 90x90 seria ilegible, asi que se listan los pares
    # (esperado -> obtenido) mas frecuentes cuando NO coinciden. Por caso: cada codigo
    # esperado que falto se empareja con cada codigo obtenido no esperado (producto),
    # o con "sin" si no se obtuvo ningun codigo.
    confusiones: dict[tuple[str, str], int] = {}
    for r in validos:
        esp = set(r["codigos_esperados"])
        obt = set(r["codigos_obtenidos"])
        faltantes = esp - obt
        sobrantes = obt - esp
        if not faltantes:
            continue
        destinos = sorted(sobrantes) if sobrantes else ["sin"]
        for e in sorted(faltantes):
            for d in destinos:
                confusiones[(e, d)] = confusiones.get((e, d), 0) + 1
    top_confusiones = sorted(confusiones.items(), key=lambda kv: (-kv[1], kv[0]))

    return {
        "n": n,
        "n_total": len(resultados),
        "matriz_confusion_nivel": matriz,
        "confusiones_codigo": top_confusiones,
        "n_error": len(resultados) - n,
        "accuracy_codigo_exacto": pct(cod_exacto, n),
        "recall_codigos": pct(recall_num, recall_den),
        "precision_codigos": pct(prec_num, prec_den),
        "accuracy_nivel_exacto": pct(nivel_exacto, n),
        "accuracy_nivel_pm1": pct(nivel_pm1, n),
        "accuracy_dominio": pct(dom_ok, n),
        "accuracy_por_certeza": acc_certeza,
    }


def _render_matriz(matriz: dict[int, dict[int, int]]) -> list[str]:
    """Matriz de confusion de nivel como tabla markdown.

    Filas = nivel esperado; columnas = nivel principal obtenido (0 = sin codigo).
    La diagonal son los aciertos exactos. Lo que cae fuera muestra EN QUE se equivoca.
    """
    if not matriz:
        return ["(sin datos)"]
    niveles_esp = sorted(matriz)
    cols = sorted({c for fila in matriz.values() for c in fila})
    enc = "esp\\obt | " + " | ".join("sin" if c == 0 else str(c) for c in cols) + " | total"
    sep = "|".join(["---"] * (len(cols) + 2))
    filas = [enc, sep]
    for ne in niveles_esp:
        fila = matriz[ne]
        total = sum(fila.values())
        celdas = []
        for c in cols:
            v = fila.get(c, 0)
            # Marcar la diagonal (acierto exacto) para que salte a la vista.
            celdas.append(f"**{v}**" if c == ne and v else str(v))
        filas.append(f"{ne} | " + " | ".join(celdas) + f" | {total}")
    return filas


def _etiqueta_codigo(codigo: str, rubrica) -> str:
    """`MAN-L07-MG-02 (n7 motor_grueso)` para leer las confusiones con contexto."""
    if codigo == "sin":
        return "sin (ningun codigo)"
    try:
        c = rubrica.cruzar(codigo)
        return f"{codigo} (n{c.nivel} {c.dominio})"
    except KeyError:
        return codigo


def _render_confusiones(confusiones, rubrica, tope: int = 20) -> list[str]:
    """Lista los pares esperado->obtenido mas frecuentes (confusiones de codigo)."""
    if not confusiones:
        return ["(sin confusiones: todos los codigos esperados salieron)"]
    filas = ["esperado -> obtenido | veces", "---|---"]
    for (esp, obt), veces in confusiones[:tope]:
        filas.append(f"{_etiqueta_codigo(esp, rubrica)} -> {_etiqueta_codigo(obt, rubrica)} | {veces}")
    return filas


def _escribir_reporte(m: dict, depurar: bool, rubrica) -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    lineas = [
        "# Reporte de medicion (validacion_100.json)",
        "",
        f"- Casos medidos: {m.get('n', 0)} (errores: {m.get('n_error', 0)})",
        f"- Fuente de texto: {'texto_control (DEPURAR)' if depurar else 'nota (texto de la tia)'}",
        "",
        "## Codigo de manifestacion",
        f"- Accuracy de codigo (conjunto exacto): {m.get('accuracy_codigo_exacto', 0)}%",
        f"- Recall de codigos: {m.get('recall_codigos', 0)}%",
        f"- Precision de codigos: {m.get('precision_codigos', 0)}%",
        "",
        "## Nivel y dominio",
        f"- Accuracy de nivel (exacto): {m.get('accuracy_nivel_exacto', 0)}%",
        f"- Accuracy de nivel (+/-1): {m.get('accuracy_nivel_pm1', 0)}%",
        f"- Accuracy de dominio: {m.get('accuracy_dominio', 0)}%",
        "",
        "## Accuracy de nivel por certeza",
    ]
    for cert, v in m.get("accuracy_por_certeza", {}).items():
        lineas.append(f"- {cert}: {v['acc_nivel']}% (n={v['n']})")
    lineas.append("")
    lineas.append("## Matriz de confusion de nivel")
    lineas.append("")
    lineas.append("Fila = nivel esperado, columna = nivel principal obtenido (`sin` = sin codigo).")
    lineas.append("La diagonal (**negrita**) son los aciertos exactos.")
    lineas.append("")
    lineas.extend(_render_matriz(m.get("matriz_confusion_nivel", {})))
    lineas.append("")
    lineas.append("## Confusiones de codigo (mas frecuentes)")
    lineas.append("")
    lineas.append("Codigo esperado que no salio -> codigo que salio en su lugar (`sin` = ninguno).")
    lineas.append("")
    lineas.extend(_render_confusiones(m.get("confusiones_codigo", []), rubrica))
    if depurar:
        lineas.append("")
        lineas.append("> NOTA: corrida con --depurar (texto_control). No es resultado reportable.")
    (EVAL_DIR / "reporte.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Mide accuracy sobre validacion_100.json.")
    parser.add_argument("--max", type=int, default=0, help="limitar numero de casos (0 = todos)")
    parser.add_argument("--depurar", action="store_true", help="usar texto_control (debug, no reportable)")
    parser.add_argument("--workers", type=int, default=4, help="hilos para correr casos en paralelo")
    args = parser.parse_args()

    rubrica = cargar_rubrica()
    retriever = Retriever.desde_archivos(rubrica=rubrica)
    with FEWSHOT_LOCAL.open(encoding="utf-8") as f:
        fewshot = json.load(f)
    ctx = construir_contexto(DatosLocal(), rubrica, retriever, fewshot)

    with VALIDACION.open(encoding="utf-8") as f:
        suite = json.load(f)
    casos = suite["casos"]
    if args.max:
        casos = casos[: args.max]

    print(f"Midiendo {len(casos)} casos ({'texto_control' if args.depurar else 'nota'})...")
    resultados: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futuros = {ex.submit(_evaluar_caso, ctx, c, args.depurar): c for c in casos}
        for i, fut in enumerate(futuros, 1):
            resultados.append(fut.result())
            if i % 10 == 0 or i == len(casos):
                print(f"  {i}/{len(casos)}")

    resultados.sort(key=lambda r: r["id_caso"])
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    with (EVAL_DIR / "resultados.jsonl").open("w", encoding="utf-8") as f:
        for r in resultados:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    m = _metricas(resultados)
    _escribir_reporte(m, args.depurar, rubrica)

    print("\n=== RESUMEN ===")
    print(f"accuracy codigo (exacto): {m.get('accuracy_codigo_exacto', 0)}%")
    print(f"recall / precision codigos: {m.get('recall_codigos', 0)}% / {m.get('precision_codigos', 0)}%")
    print(f"accuracy nivel exacto / +-1: {m.get('accuracy_nivel_exacto', 0)}% / {m.get('accuracy_nivel_pm1', 0)}%")
    print(f"accuracy dominio: {m.get('accuracy_dominio', 0)}%")
    print("\nMatriz de confusion de nivel (fila=esperado, col=obtenido, sin=sin codigo):")
    for linea in _render_matriz(m.get("matriz_confusion_nivel", {})):
        print("  " + linea.replace("**", ""))
    print("\nConfusiones de codigo mas frecuentes (esperado -> obtenido):")
    for linea in _render_confusiones(m.get("confusiones_codigo", []), rubrica, tope=10):
        print("  " + linea)
    print(f"\nreporte -> {EVAL_DIR / 'reporte.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
