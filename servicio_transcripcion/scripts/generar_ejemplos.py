"""Regenera contrato/ejemplos/*.json con el mismo código que usa el servicio.

Uso: python scripts/generar_ejemplos.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from transcriptor.config import Config  # noqa: E402
from transcriptor.conversion import convertir_salida  # noqa: E402
from transcriptor.servicio import ServicioTranscribe  # noqa: E402

TRABAJO = {
    "TranscriptionJobName": "tr-CAP-000012",
    "LanguageCode": "es-US",
    "CreationTime": datetime(2026, 10, 15, 14, 2, 11, tzinfo=timezone.utc),
    "CompletionTime": datetime(2026, 10, 15, 14, 2, 38, tzinfo=timezone.utc),
}


def main() -> None:
    servicio = ServicioTranscribe(Config(bucket="ejemplo"), s3=None, transcribe=None)
    crudo = json.loads((RAIZ / "src" / "transcriptor" / "datos" / "ejemplo_transcribe.json").read_text(encoding="utf-8"))
    texto, palabras, promedio = convertir_salida(crudo, servicio.config.umbral_palabra_dudosa)
    ejemplos = {
        "transcribiendo": servicio._armar(TRABAJO, "transcribiendo"),
        "completado": servicio._armar(TRABAJO, "completado", texto=texto, palabras=palabras, promedio=promedio),
        "fallido": servicio._fallido(
            TRABAJO, "transcripcion_fallida", "Ejemplo: aquí va el motivo que informa Amazon Transcribe (FailureReason)"
        ),
    }
    for nombre, resultado in ejemplos.items():
        destino = RAIZ / "contrato" / "ejemplos" / f"{nombre}.json"
        destino.write_text(
            json.dumps(resultado.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"escrito {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()