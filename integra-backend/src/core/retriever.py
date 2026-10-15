"""Recuperacion por embeddings sobre las 90 manifestaciones (coseno, Python puro).

- Los embeddings de la rubrica se calculan una vez (scripts/embeber_rubrica.py) y se
  guardan en data/processed/embeddings_rubrica.json (o en S3 en AWS).
- En la Lambda se embebe cada consulta (la `accion` interpretada de una conducta) y se
  compara por coseno contra las 90, SIN filtro de nivel (dominio.md Seccion 1 y 5).
- Se embebe `"<dominio>: <texto_observable>"` (sin el numero de nivel, para no sesgar).

Como Titan V2 devuelve vectores normalizados (normalize=True), el coseno es el producto
punto; aun asi se normaliza en codigo por robustez.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config as BotoConfig

from .config import EMBEDDINGS_LOCAL, config
from .rubrica import Rubrica, cargar_rubrica

# Version del esquema del archivo de embeddings (para detectar incompatibilidades).
FORMATO_EMBEDDINGS = 1


def texto_a_embeber(dominio: str, texto_observable: str) -> str:
    """La cadena que se embebe por codigo: dominio + texto, SIN el nivel."""
    return f"{dominio}: {texto_observable}"


# --- Cliente Bedrock (perezoso) ---

_cliente = None


def _bedrock():
    global _cliente
    if _cliente is None:
        _cliente = boto3.client(
            "bedrock-runtime",
            region_name=config.region,
            config=BotoConfig(retries={"max_attempts": 2, "mode": "standard"}),
        )
    return _cliente


def embeber(texto: str, model_id: str | None = None) -> list[float]:
    """Embebe un texto con Titan Text Embeddings V2 y devuelve el vector."""
    mid = model_id or config.model_id_embeddings
    if not mid:
        raise ValueError("falta MODEL_ID_EMBEDDINGS")
    cuerpo = json.dumps({"inputText": texto, "normalize": True})
    resp = _bedrock().invoke_model(modelId=mid, body=cuerpo)
    datos = json.loads(resp["body"].read())
    return datos["embedding"]


# --- Algebra de vectores (Python puro) ---

def _normalizar(v: list[float]) -> list[float]:
    norma = math.sqrt(sum(x * x for x in v))
    if norma == 0:
        return v
    return [x / norma for x in v]


def coseno(a: list[float], b: list[float]) -> float:
    """Similitud coseno entre dos vectores (asume que pueden no estar normalizados)."""
    na = _normalizar(a)
    nb = _normalizar(b)
    return sum(x * y for x, y in zip(na, nb, strict=True))


# --- Resultado de busqueda ---

@dataclass(frozen=True)
class Candidata:
    id_manifestacion: str
    dominio: str
    texto_observable: str
    nivel: int
    score: float


# --- Retriever ---

class Retriever:
    """Busqueda por embeddings sobre las 90 manifestaciones (sin filtro de nivel)."""

    def __init__(self, rubrica: Rubrica, embeddings: dict[str, list[float]]) -> None:
        self.rubrica = rubrica
        # Pre-normalizar los vectores de la rubrica una sola vez.
        self._emb: dict[str, list[float]] = {
            codigo: _normalizar(vec) for codigo, vec in embeddings.items()
        }
        faltan = set(rubrica.codigos) - set(self._emb)
        if faltan:
            raise ValueError(f"faltan embeddings para {len(faltan)} codigos: {sorted(faltan)[:3]}...")

    # --- Carga ---

    @classmethod
    def desde_archivos(
        cls,
        ruta_embeddings: str | Path = EMBEDDINGS_LOCAL,
        rubrica: Rubrica | None = None,
    ) -> Retriever:
        rub = rubrica if rubrica is not None else cargar_rubrica()
        with Path(ruta_embeddings).open(encoding="utf-8") as f:
            datos = json.load(f)
        return cls(rub, _extraer_vectores(datos))

    @classmethod
    def desde_dict(cls, rubrica: Rubrica, datos: dict[str, Any]) -> Retriever:
        return cls(rubrica, _extraer_vectores(datos))

    # --- Busqueda ---

    def buscar(self, consulta: str, k: int, *, model_id: str | None = None) -> list[Candidata]:
        """Embebe la consulta y devuelve las k manifestaciones mas similares (coseno)."""
        vec = _normalizar(embeber(consulta, model_id))
        return self.buscar_con_vector(vec, k)

    def buscar_con_vector(self, vector: list[float], k: int) -> list[Candidata]:
        """Igual que buscar() pero con un vector de consulta ya calculado (para tests)."""
        q = _normalizar(vector)
        puntuadas: list[tuple[str, float]] = [
            (codigo, sum(x * y for x, y in zip(q, vec, strict=True)))
            for codigo, vec in self._emb.items()
        ]
        puntuadas.sort(key=lambda t: t[1], reverse=True)

        resultado: list[Candidata] = []
        for codigo, score in puntuadas[:k]:
            cruce = self.rubrica.cruzar(codigo)
            resultado.append(
                Candidata(
                    id_manifestacion=codigo,
                    dominio=cruce.dominio,
                    texto_observable=cruce.texto_observable,
                    nivel=cruce.nivel,
                    score=score,
                )
            )
        return resultado


def _extraer_vectores(datos: dict[str, Any]) -> dict[str, list[float]]:
    """Soporta tanto {"manifestaciones": {codigo: {embedding: [...]}}} como {codigo: [...]}."""
    if "manifestaciones" in datos:
        return {c: m["embedding"] for c, m in datos["manifestaciones"].items()}
    # Formato plano: {codigo: [vector]}
    return {c: v for c, v in datos.items() if not c.startswith("_") and isinstance(v, list)}
