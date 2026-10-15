"""Genera data/processed/embeddings_rubrica.json con Titan Text Embeddings V2.

Embebe `"<dominio>: <texto_observable>"` de cada una de las 90 manifestaciones
(sin el numero de nivel, para no sesgar la busqueda) y guarda los vectores.

Uso (con el .env cargado o las credenciales en el entorno):
    py -3.13 scripts/embeber_rubrica.py
    py -3.13 scripts/embeber_rubrica.py --salida data/processed/embeddings_rubrica.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from core.config import EMBEDDINGS_LOCAL, config
from core.retriever import FORMATO_EMBEDDINGS, embeber, texto_a_embeber
from core.rubrica import cargar_rubrica


def main() -> int:
    parser = argparse.ArgumentParser(description="Embebe la rubrica con Titan V2.")
    parser.add_argument("--salida", default=str(EMBEDDINGS_LOCAL), help="ruta del JSON de salida")
    args = parser.parse_args()

    if not config.model_id_embeddings:
        print("ERROR: falta MODEL_ID_EMBEDDINGS en el entorno (.env).", file=sys.stderr)
        return 1

    rubrica = cargar_rubrica()
    codigos = rubrica.codigos
    print(f"Embebiendo {len(codigos)} manifestaciones con {config.model_id_embeddings}...")

    manifestaciones: dict[str, dict] = {}
    dim = None
    t0 = time.monotonic()
    for i, codigo in enumerate(codigos, 1):
        cruce = rubrica.cruzar(codigo)
        texto = texto_a_embeber(cruce.dominio, cruce.texto_observable)
        vector = embeber(texto)
        if dim is None:
            dim = len(vector)
        manifestaciones[codigo] = {"texto": texto, "embedding": vector}
        if i % 10 == 0 or i == len(codigos):
            print(f"  {i}/{len(codigos)}")

    salida = {
        "_formato": FORMATO_EMBEDDINGS,
        "version_rubrica": rubrica.version,
        "model_id": config.model_id_embeddings,
        "dim": dim,
        "manifestaciones": manifestaciones,
    }

    ruta = Path(args.salida)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)

    segundos = time.monotonic() - t0
    print(f"Listo: {len(manifestaciones)} vectores (dim {dim}) en {ruta} ({segundos:.1f}s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
