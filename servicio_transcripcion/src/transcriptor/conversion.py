"""Convierte el JSON de salida de Amazon Transcribe al texto y las palabras del contrato."""
from __future__ import annotations

import unicodedata
from typing import Any

from .contrato import Palabra


def _nfc(texto: str) -> str:
    return unicodedata.normalize("NFC", texto)


def _segundos(valor: Any) -> float | None:
    return None if valor is None else round(float(valor), 3)


def convertir_salida(datos: dict[str, Any], umbral: float) -> tuple[str, list[Palabra], float | None]:
    """Devuelve (texto_completo, palabras, confianza_agregada).

    La puntuación queda fuera de palabras: Transcribe le asigna confianza 0 y siempre saldría dudosa.
    """
    try:
        resultados = datos["results"]
        texto = " ".join(t["transcript"] for t in resultados.get("transcripts", []))
        palabras: list[Palabra] = []
        confianzas: list[float] = []
        for item in resultados.get("items", []):
            if item.get("type") != "pronunciation":
                continue
            alternativa = item["alternatives"][0]
            confianza = min(max(float(alternativa["confidence"]), 0.0), 1.0)
            confianzas.append(confianza)
            palabras.append(
                Palabra(
                    texto=_nfc(alternativa["content"]),
                    inicio_segundos=_segundos(item.get("start_time")),
                    fin_segundos=_segundos(item.get("end_time")),
                    confianza=round(confianza, 4),
                    dudosa=confianza < umbral,
                )
            )
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
        raise ValueError("La salida de Amazon Transcribe no tiene el formato esperado") from exc
    promedio = round(sum(confianzas) / len(confianzas), 4) if confianzas else None
    return _nfc(texto).strip(), palabras, promedio