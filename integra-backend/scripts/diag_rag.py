r"""Diagnostico del checkpoint: para los casos que fallan en la clasificacion, muestra
las conductas extraidas y las candidatas que trae el RAG, y marca si el codigo
esperado esta entre ellas. Ayuda a decidir si el problema es el RAG (candidatas) o
la decision del LLM. No corre las N corridas (es rapido).

Uso:
    .\.venv\Scripts\python.exe scripts\diag_rag.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from core.config import config
from core.llm import call_json, cargar_esquema
from core.retriever import Retriever
from core.rubrica import cargar_rubrica

# (id, protagonista, texto literal del fragmento, codigos "buenos" segun dominio.md).
CASOS = [
    (
        "C1",
        "Nayara",
        (
            "cuando salia del bano se da cuenta que a la tia se le caen los individuales, "
            "ella se agacha, recoge los individuales, los ordena y se los pasa a la tia"
        ),
        ["MAN-L09-SE-01", "MAN-L09-SE-02"],  # colaboracion espontanea (nivel 9 socioemocional)
    ),
    (
        "C2",
        "Sofia",
        'mira por la ventana y dice "viene el Alexi"',
        ["MAN-L08-LC-01", "MAN-L09-LC-01"],  # combina 2 / 3+ palabras (lenguaje 8 o 9)
    ),
    (
        "C3",
        "Nayara",
        "tia mira la Pascal tiene moco",
        ["MAN-L09-LC-01"],  # frase de 3+ palabras (lenguaje 9)
    ),
]


def main() -> int:
    rub = cargar_rubrica()
    retr = Retriever.desde_archivos(rubrica=rub)
    sch_cond = cargar_esquema("extraer_conductas")

    for cid, prot, texto, esperados in CASOS:
        print("=" * 72)
        print(f"{cid}  protagonista={prot}")
        print(f"texto: {texto}")
        print(f"codigos esperados (orientativo): {esperados}")

        cond, _ = call_json(
            "extraer_conductas",
            {"protagonista": prot, "texto": texto},
            sch_cond,
            config.model_id_conductas,
            rubrica=rub,
        )
        print(f"evaluable={cond.get('evaluable')}")
        for c in cond.get("conductas", []):
            print(f"  conducta: accion={c.get('accion')!r}")

        vistos: dict[str, object] = {}
        for c in cond.get("conductas", []):
            acc = c.get("accion", "")
            if not acc:
                continue
            for cand in retr.buscar(acc, k=config.top_k):
                vistos.setdefault(cand.id_manifestacion, cand)
        cands = list(vistos.values())[: 2 * config.top_k]

        presentes = [e for e in esperados if e in vistos]
        print(f"CANDIDATAS RAG ({len(cands)}) | esperados presentes: {presentes or 'NINGUNO'}")
        for cand in cands:
            marca = " <== ESPERADO" if cand.id_manifestacion in esperados else ""
            print(
                f"  {cand.id_manifestacion} | n{cand.nivel} | {cand.dominio:<22} "
                f"| score={cand.score:.3f}{marca}"
            )
    print("=" * 72)
    print(f"TOP_K actual = {config.top_k} (pool maximo = {2 * config.top_k})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
