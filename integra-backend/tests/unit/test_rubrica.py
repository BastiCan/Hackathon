"""Tarea 2: la rubrica cruza bien y el few-shot cumple el esquema de salida.

No se hardcodea la cantidad de niveles/codigos como constante del codigo (tech.md);
pero el dataset E-1 que se versiona debe cumplir su forma conocida (9 niveles,
5 dominios, 90 codigos = 2 por nivel x dominio), asi que se verifica como dato.
"""

from __future__ import annotations

import json

import pytest
from jsonschema import Draft202012Validator

from core.config import FEWSHOT_LOCAL
from core.rubrica import Rubrica, cargar_rubrica, resolver_esquema

SCHEMA_CLASIFICAR = "src/schemas/clasificar.json"

# Valores conocidos del dataset E-1 (no son constantes del codigo: son del archivo).
E1_NIVELES = 9
E1_DOMINIOS = 5
E1_CODIGOS = 90


@pytest.fixture(scope="module")
def rubrica() -> Rubrica:
    return cargar_rubrica()


def test_rubrica_forma_e1(rubrica: Rubrica) -> None:
    assert len(rubrica.niveles) == E1_NIVELES
    assert len(rubrica.dominios) == E1_DOMINIOS
    assert len(rubrica.codigos) == E1_CODIGOS


def test_niveles_consecutivos_desde_1(rubrica: Rubrica) -> None:
    numeros = rubrica.numeros_de_nivel
    assert numeros == list(range(1, len(numeros) + 1))


def test_cada_codigo_cruza_a_nivel_y_dominio_validos(rubrica: Rubrica) -> None:
    niveles_validos = set(rubrica.numeros_de_nivel)
    dominios_validos = set(rubrica.dominios)
    for codigo in rubrica.codigos:
        cruce = rubrica.cruzar(codigo)
        assert cruce.id_manifestacion == codigo
        assert cruce.nivel in niveles_validos
        assert cruce.dominio in dominios_validos
        assert cruce.texto_observable.strip() != ""


def test_dos_codigos_por_nivel_y_dominio(rubrica: Rubrica) -> None:
    # El E-1 tiene exactamente 2 manifestaciones por (nivel, dominio).
    conteo: dict[tuple[int, str], int] = {}
    for codigo in rubrica.codigos:
        c = rubrica.cruzar(codigo)
        conteo[(c.nivel, c.dominio)] = conteo.get((c.nivel, c.dominio), 0) + 1
    assert len(conteo) == len(rubrica.numeros_de_nivel) * len(rubrica.dominios)
    assert all(v == 2 for v in conteo.values())


def test_cruzar_codigo_inexistente_lanza(rubrica: Rubrica) -> None:
    with pytest.raises(KeyError):
        rubrica.cruzar("MAN-NO-EXISTE-99")


# --- Few-shot ---

@pytest.fixture(scope="module")
def fewshot() -> dict:
    with FEWSHOT_LOCAL.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def validador_clasificar(rubrica: Rubrica) -> Draft202012Validator:
    with open(SCHEMA_CLASIFICAR, encoding="utf-8") as f:
        esquema = json.load(f)
    # Igual que llm.py: resolver x-enum-from contra la rubrica antes de validar.
    esquema_resuelto = resolver_esquema(esquema, rubrica)
    Draft202012Validator.check_schema(esquema_resuelto)
    return Draft202012Validator(esquema_resuelto)


def test_fewshot_tiene_un_ejemplo_por_nivel(fewshot: dict, rubrica: Rubrica) -> None:
    ejemplos = fewshot["ejemplos"]
    assert len(ejemplos) == len(rubrica.numeros_de_nivel)
    niveles_cubiertos = set()
    for ej in ejemplos:
        # El ejemplo evidencia un codigo; su nivel sale del cruce con la rubrica.
        codigos = [m["id_manifestacion"] for m in ej["respuesta"]["manifestaciones"]]
        assert codigos, "cada ejemplo del few-shot evidencia al menos un codigo"
        for codigo in codigos:
            niveles_cubiertos.add(rubrica.cruzar(codigo).nivel)
    assert niveles_cubiertos == set(rubrica.numeros_de_nivel)


def test_cada_respuesta_fewshot_valida_contra_esquema(
    fewshot: dict, validador_clasificar: Draft202012Validator
) -> None:
    for ej in fewshot["ejemplos"]:
        errores = sorted(validador_clasificar.iter_errors(ej["respuesta"]), key=str)
        assert not errores, (
            f"la respuesta del ejemplo {ej['id_observacion_origen']} no valida: "
            f"{[e.message for e in errores]}"
        )


def test_codigos_fewshot_existen_en_rubrica(fewshot: dict, rubrica: Rubrica) -> None:
    for ej in fewshot["ejemplos"]:
        for m in ej["respuesta"]["manifestaciones"]:
            assert rubrica.existe(m["id_manifestacion"])
        otro = ej["respuesta"]["otro_codigo_viable"]
        # En el E-1 es null a proposito; si existiera, debe ser un codigo valido.
        assert otro is None or rubrica.existe(otro)
