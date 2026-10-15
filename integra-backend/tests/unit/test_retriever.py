"""Tarea 5: retriever (coseno Python puro) sobre las 90 manifestaciones.

La parte de coseno/carga no llama a Bedrock: usa el archivo de embeddings ya generado
y vectores de consulta pre-calculados. (La busqueda que embebe una consulta real vive
en tests/llm.)
"""

from __future__ import annotations

import json

import pytest

from core.config import EMBEDDINGS_LOCAL
from core.retriever import Retriever, coseno, texto_a_embeber
from core.rubrica import cargar_rubrica

pytestmark = pytest.mark.skipif(
    not EMBEDDINGS_LOCAL.is_file(),
    reason="requiere data/processed/embeddings_rubrica.json (correr scripts/embeber_rubrica.py)",
)


@pytest.fixture(scope="module")
def retriever() -> Retriever:
    return Retriever.desde_archivos()


@pytest.fixture(scope="module")
def embeddings_crudos() -> dict:
    with EMBEDDINGS_LOCAL.open(encoding="utf-8") as f:
        return json.load(f)


def test_texto_a_embeber_sin_nivel() -> None:
    s = texto_a_embeber("cognitivo", "Clasifica objetos por una caracteristica visible.")
    assert s == "cognitivo: Clasifica objetos por una caracteristica visible."
    assert "nivel" not in s.lower()
    assert "L0" not in s  # no se cuela el codigo/nivel


def test_coseno_identico_y_ortonormal() -> None:
    assert coseno([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert coseno([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert coseno([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)


def test_retriever_cubre_las_90(retriever: Retriever) -> None:
    rubrica = cargar_rubrica()
    assert set(retriever._emb) == set(rubrica.codigos)


def test_buscar_con_vector_recupera_el_mismo_codigo(
    retriever: Retriever, embeddings_crudos: dict
) -> None:
    # Tomamos el vector embebido de un codigo y buscamos: debe salir primero el mismo.
    manifest = embeddings_crudos["manifestaciones"]
    codigo = "MAN-L09-CO-02"
    vector = manifest[codigo]["embedding"]
    resultado = retriever.buscar_con_vector(vector, k=5)
    assert resultado[0].id_manifestacion == codigo
    assert resultado[0].score == pytest.approx(1.0, abs=1e-6)


def test_buscar_devuelve_k_candidatas_con_cruce(
    retriever: Retriever, embeddings_crudos: dict
) -> None:
    codigo = "MAN-L08-LC-01"
    vector = embeddings_crudos["manifestaciones"][codigo]["embedding"]
    resultado = retriever.buscar_con_vector(vector, k=8)
    assert len(resultado) == 8
    # Cada candidata trae el cruce con la rubrica (nivel, dominio, texto).
    for c in resultado:
        assert c.nivel >= 1
        assert c.dominio != ""
        assert c.texto_observable != ""
    # Scores ordenados de mayor a menor.
    scores = [c.score for c in resultado]
    assert scores == sorted(scores, reverse=True)


def test_vecinos_cercanos_aparecen_sin_filtro_de_nivel(
    retriever: Retriever, embeddings_crudos: dict
) -> None:
    # Para una conducta motora gruesa, la busqueda debe traer varios niveles (no filtra).
    codigo = "MAN-L07-MG-02"
    vector = embeddings_crudos["manifestaciones"][codigo]["embedding"]
    resultado = retriever.buscar_con_vector(vector, k=10)
    niveles = {c.nivel for c in resultado}
    assert len(niveles) >= 2  # trae manifestaciones de mas de un nivel
