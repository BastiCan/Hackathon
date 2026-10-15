"""Corre el pipeline completo en el computador (Bedrock real, datos locales).

Uso:
  py -3.13 scripts/pipeline_local.py --texto "..." --educadora EDU-0001 --sala SG-A --fecha 2026-10-15
  py -3.13 scripts/pipeline_local.py --casos tests/fixtures/notas_prueba.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from core.config import FEWSHOT_LOCAL
from core.datos import DatosLocal
from core.modelos import Entrada
from core.pipeline import ErrorCapturaExc, procesar_nota
from core.retriever import Retriever
from core.rubrica import cargar_rubrica


def _cargar_fewshot() -> dict:
    with FEWSHOT_LOCAL.open(encoding="utf-8") as f:
        return json.load(f)


def _resultado_a_dict(resultado) -> dict:
    return {
        "id_captura": resultado.id_captura,
        "advertencias": resultado.advertencias,
        "observaciones": [o.model_dump(mode="json", exclude_none=True) for o in resultado.observaciones],
    }


def _run_uno(args) -> int:
    rubrica = cargar_rubrica()
    retriever = Retriever.desde_archivos(rubrica=rubrica)
    fewshot = _cargar_fewshot()
    datos = DatosLocal()
    entrada = Entrada(
        texto=args.texto,
        id_educadora=args.educadora,
        sala_grupo=args.sala,
        fecha=date.fromisoformat(args.fecha),
    )
    try:
        resultado = procesar_nota(entrada, datos, rubrica, retriever, fewshot)
    except ErrorCapturaExc as e:
        print(json.dumps({"error": {"codigo": e.codigo.value}}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(_resultado_a_dict(resultado), ensure_ascii=False, indent=2))
    return 0


def _resumen_obs(o) -> str:
    if o.tipo.value == "PARTICULAR":
        nivel = o.nivel if o.nivel is not None else "null"
        doms = ",".join(sorted({m.dominio for m in o.manifestaciones})) or "-"
        ev = o.evaluabilidad.value if o.evaluabilidad else "-"
        return f"PARTICULAR {o.id_nino} {ev} nivel={nivel} dom={doms} cert={o.certeza.value if o.certeza else '-'}"
    if o.tipo.value == "NO_IDENTIFICADO":
        return f"NO_IDENTIFICADO {o.error_identificacion.value if o.error_identificacion else '?'}"
    return "GENERAL"


def _run_casos(args) -> int:
    rubrica = cargar_rubrica()
    retriever = Retriever.desde_archivos(rubrica=rubrica)
    fewshot = _cargar_fewshot()
    datos = DatosLocal()

    with Path(args.casos).open(encoding="utf-8") as f:
        suite = json.load(f)
    contexto = suite["contexto"]
    fecha = date.fromisoformat(contexto["fecha"])

    # Ademas de imprimir, se escribe la tabla fila por fila a data/eval/tabla_casos.md
    # (con flush), para que la salida sobreviva aunque el proceso se interrumpa.
    salida = RAIZ / "data" / "eval" / "tabla_casos.md"
    salida.parent.mkdir(parents=True, exist_ok=True)
    f_out = salida.open("w", encoding="utf-8")

    def emitir(linea: str) -> None:
        print(linea, flush=True)
        f_out.write(linea + "\n")
        f_out.flush()

    try:
        emitir(f"{'ID':<5} | {'ESPERADO':<48} | OBTENIDO")
        emitir("-" * 110)
        for caso in suite["casos"]:
            entrada = Entrada(
                texto=caso["texto"],
                id_educadora=contexto["id_educadora"],
                sala_grupo=contexto["sala_grupo"],
                fecha=fecha,
            )
            try:
                resultado = procesar_nota(entrada, datos, rubrica, retriever, fewshot)
                obtenido = " ; ".join(_resumen_obs(o) for o in resultado.observaciones)
            except ErrorCapturaExc as e:
                obtenido = f"ERROR {e.codigo.value}"
            esperado = _resumen_esperado(caso.get("esperado", []))
            emitir(f"{caso['id']:<5} | {esperado:<48} | {obtenido}")
    finally:
        f_out.close()
    return 0


def _resumen_esperado(esperado) -> str:
    if isinstance(esperado, dict):
        esperado = [esperado]
    partes = []
    for e in esperado:
        tipo = e.get("tipo", "?")
        if tipo == "PARTICULAR":
            nivel = e.get("nivel", "-")
            partes.append(f"PART {e.get('id_nino','?')} n={nivel}")
        elif tipo == "NO_IDENTIFICADO":
            partes.append(f"NOID {e.get('error_identificacion','?')}")
        else:
            partes.append(tipo)
    return " ; ".join(partes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Corre el pipeline en local.")
    parser.add_argument("--texto")
    parser.add_argument("--educadora", default="EDU-0001")
    parser.add_argument("--sala", default="SG-A")
    parser.add_argument("--fecha", default="2026-10-15")
    parser.add_argument("--casos", help="ruta a notas_prueba.json para correr todos")
    args = parser.parse_args()

    if args.casos:
        return _run_casos(args)
    if args.texto:
        return _run_uno(args)
    parser.error("usa --texto o --casos")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
