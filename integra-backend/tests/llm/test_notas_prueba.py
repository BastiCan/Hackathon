"""Tarea 6.4: casos de tests/fixtures/notas_prueba.json (marcado -m llm).

Prueba de integracion con Bedrock real. Estos casos verifican SEPARACION (general/
particular), IDENTIFICACION del nino/a y deteccion de lo NO evaluable. NO verifican
nivel ni dominio (eso se mide con validacion_100.json). No corre por defecto.
"""

from __future__ import annotations

import json
import os
from datetime import date

import pytest

from core.config import FEWSHOT_LOCAL
from core.datos import DatosLocal
from core.modelos import Entrada, TipoObservacion
from core.pipeline import procesar_nota
from core.retriever import Retriever
from core.rubrica import cargar_rubrica

pytestmark = pytest.mark.llm


def _modelos_listos() -> bool:
    return all(
        os.environ.get(k)
        for k in ("MODEL_ID_SEPARAR", "MODEL_ID_CONDUCTAS", "MODEL_ID_EVALUAR", "MODEL_ID_EMBEDDINGS")
    )


requiere_modelos = pytest.mark.skipif(
    not _modelos_listos(), reason="requiere los MODEL_ID_* en el entorno"
)


@pytest.fixture(scope="module")
def contexto():
    rubrica = cargar_rubrica()
    retriever = Retriever.desde_archivos(rubrica=rubrica)
    with FEWSHOT_LOCAL.open(encoding="utf-8") as f:
        fewshot = json.load(f)
    return rubrica, retriever, fewshot


@pytest.fixture(scope="module")
def suite() -> dict:
    from core.datos import NOMINA_DEMO

    ruta = NOMINA_DEMO.parent / "notas_prueba.json"
    with ruta.open(encoding="utf-8") as f:
        return json.load(f)


def _procesar(caso, suite, contexto):
    rubrica, retriever, fewshot = contexto
    ctx = suite["contexto"]
    entrada = Entrada(
        texto=caso["texto"],
        id_educadora=ctx["id_educadora"],
        sala_grupo=ctx["sala_grupo"],
        fecha=date.fromisoformat(ctx["fecha"]),
    )
    datos = DatosLocal()
    return procesar_nota(entrada, datos, rubrica, retriever, fewshot)


def _esperado_lista(caso):
    esp = caso.get("esperado", [])
    return esp if isinstance(esp, list) else [esp]


@requiere_modelos
@pytest.mark.parametrize(
    "caso_id", ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "I1", "I2", "I3", "I4", "I5", "P1"]
)
def test_casos_notas_prueba(caso_id, suite, contexto) -> None:
    caso = next(c for c in suite["casos"] if c["id"] == caso_id)
    resultado = _procesar(caso, suite, contexto)
    esperados = _esperado_lista(caso)

    # Agrupar observaciones obtenidas por tipo para comparar.
    por_nino = {o.id_nino: o for o in resultado.observaciones if o.id_nino}
    tipos_obtenidos = [o.tipo for o in resultado.observaciones]

    for e in esperados:
        tipo = e.get("tipo")
        if tipo == "GENERAL":
            assert TipoObservacion.GENERAL in tipos_obtenidos
        elif tipo == "NO_IDENTIFICADO":
            errores = {
                o.error_identificacion.value
                for o in resultado.observaciones
                if o.tipo == TipoObservacion.NO_IDENTIFICADO and o.error_identificacion
            }
            assert e["error_identificacion"] in errores
        elif tipo == "PARTICULAR":
            idn = e.get("id_nino")
            assert idn in por_nino, f"falta observacion para {idn}"
            obs = por_nino[idn]
            assert obs.tipo == TipoObservacion.PARTICULAR
            if "evaluabilidad" in e:
                assert obs.evaluabilidad.value == e["evaluabilidad"]


@requiere_modelos
def test_c3_no_evaluable_sin_pascal(suite, contexto) -> None:
    # C3: la observacion de Naiara (NINO-00487) es NO_EVALUABLE (estado de salud de otro,
    # sin conducta propia) con nivel None; Pascal (NINO-00051) solo mencionado -> sin obs.
    caso = next(c for c in suite["casos"] if c["id"] == "C3")
    resultado = _procesar(caso, suite, contexto)

    obs = next((o for o in resultado.observaciones if o.id_nino == "NINO-00487"), None)
    assert obs is not None, "falta observacion para NINO-00487"
    assert obs.evaluabilidad.value == "NO_EVALUABLE"
    assert obs.nivel is None  # nunca 0

    ids_con_obs = {o.id_nino for o in resultado.observaciones if o.id_nino}
    assert "NINO-00051" not in ids_con_obs, "Pascal es mencionado, no debe tener observacion"


@requiere_modelos
@pytest.mark.parametrize("caso_id", ["C6", "C7"])
def test_general_unico_fragmento(caso_id, suite, contexto) -> None:
    # C6 y C7: notas del grupo -> un unico fragmento GENERAL, sin particulares ni no-identificados.
    caso = next(c for c in suite["casos"] if c["id"] == caso_id)
    resultado = _procesar(caso, suite, contexto)
    assert len(resultado.observaciones) == 1
    assert resultado.observaciones[0].tipo == TipoObservacion.GENERAL
