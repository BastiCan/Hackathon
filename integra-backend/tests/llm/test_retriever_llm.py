"""Tarea 5: busqueda con embedding real de la consulta (marcada -m llm)."""

from __future__ import annotations

import os

import pytest

from core.config import EMBEDDINGS_LOCAL
from core.retriever import Retriever

pytestmark = pytest.mark.llm


@pytest.mark.skipif(
    not os.environ.get("MODEL_ID_EMBEDDINGS") or not EMBEDDINGS_LOCAL.is_file(),
    reason="requiere MODEL_ID_EMBEDDINGS y embeddings_rubrica.json",
)
def test_buscar_consulta_real_trae_dominio_esperado() -> None:
    retriever = Retriever.desde_archivos()
    # Una conducta de clasificacion deberia traer manifestaciones del dominio cognitivo.
    resultado = retriever.buscar("clasifica objetos por su tamano", k=8)
    assert len(resultado) == 8
    dominios = [c.dominio for c in resultado]
    assert "cognitivo" in dominios
    # El top-1 de una consulta de clasificacion debe ser una manifestacion cognitiva
    # de clasificar (Titan V2 da cosenos moderados para textos cortos semanticamente
    # cercanos; el valor absoluto importa menos que el orden relativo).
    assert resultado[0].dominio == "cognitivo"
    assert resultado[0].score > 0.25
