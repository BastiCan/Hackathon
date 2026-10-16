"""Pruebas de `datos/decisiones.py`: la regla 7 y la tabla Decisiones.

Sin AWS: DynamoDB entra por dobles de `dynamo` y `mapeo.a_sugerencia`, así que ninguna
prueba abre una conexión. `test_rutas_decisiones.py` reutiliza los ayudantes de acá.
"""
from __future__ import annotations

import pytest

from huellita_api import auth, errores, tiempo
from huellita_api.config import cargar_config
from huellita_api.datos import decisiones, lectura
from huellita_api.modelos import Cambios, ItemDecision, Original, Sugerencia

__all__ = ["auth", "errores", "lectura", "tiempo"]  # los usa test_rutas_decisiones.py


def sin_aws(nombre: str):
    """Doble que falla si alguien llama a AWS sin haberlo reemplazado."""

    def doble(*_argumentos: object, **_llaves: object) -> object:
        raise AssertionError(f"las pruebas no llaman a {nombre} sin reemplazarlo")

    return doble


CFG = cargar_config(
    {
        "TABLA_NINOS": "NinosPrueba",
        "TABLA_OBSERVACIONES": "ObservacionesPrueba",
        "TABLA_DECISIONES": "DecisionesPrueba",
        "JARDIN_DEMO": "JAR-0001",
        "SALAS_DEMO": "SG-A,SG-B",
    }
)
SALA_KEY = CFG.sala_key("SG-A")
ID_CAPTURA = "CAP-01M503FN5942S3MNAFA14C07AQ"
ID_SUG = f"{ID_CAPTURA}-p0-0"
ID_DATASET = "OBS-0000042~cognitivo"
VALIDADA_EN = "2026-10-15T14:05:57-03:00"
CAMBIOS_DISTINTOS = {"ninoId": "NINO-00263", "nucleo": "cognitivo", "nivel": 4}
CAMBIOS_IGUALES = {"ninoId": "NINO-00253", "nucleo": "lenguaje_comunicacion", "nivel": 9}
ORIGINAL_IA = Original(ninoId="NINO-00253", nucleo="lenguaje_comunicacion", nivel=9)


def sugerencia(**cambios: object) -> Sugerencia:
    """Una sugerencia de la app como la deja la IA en Observaciones."""
    base: dict[str, object] = {
        "id": ID_SUG,
        "evidenciaId": ID_CAPTURA,
        "salaId": "SG-A",
        "tipo": "evaluacion",
        "ninoId": "NINO-00253",
        "nucleo": "lenguaje_comunicacion",
        "nivel": 9,
        "conducta": "Produce combinaciones de tres o más palabras para relatar o pedir.",
        "cita": "Pedro apiló tres bloques y después contó 'uno, dos, tres'.",
        "certeza": "media",
        "estado": "pendiente",
    }
    return Sugerencia(**(base | cambios))


def item(estado: str = "aceptada", cambios: dict | None = None, id_sugerencia: str = ID_SUG) -> ItemDecision:
    return ItemDecision(
        idSugerencia=id_sugerencia,
        estado=estado,
        cambios=Cambios(**cambios) if cambios is not None else None,
    )


# --- Regla 7: las cinco transiciones -------------------------------------------------


def test_decidir_aceptada_sin_cambios_no_guarda_original() -> None:
    assert decisiones.decidir(sugerencia(), item("aceptada")) == ("aceptada", None)


def test_decidir_cambiada_guarda_el_original_de_la_ia() -> None:
    assert decisiones.decidir(sugerencia(), item("aceptada", CAMBIOS_DISTINTOS)) == ("cambiada", ORIGINAL_IA)


def test_decidir_aceptada_cuando_los_cambios_igualan_a_la_ia() -> None:
    assert decisiones.decidir(sugerencia(), item("aceptada", CAMBIOS_IGUALES)) == ("aceptada", None)


def test_decidir_descartada() -> None:
    assert decisiones.decidir(sugerencia(), item("descartada")) == ("descartada", None)


def test_decidir_pendiente_no_guarda_nada() -> None:
    assert decisiones.decidir(sugerencia(), item("pendiente")) == ("pendiente", None)


def test_decidir_repetido_sobre_una_sugerencia_ya_cambiada_da_lo_mismo() -> None:
    """Idempotencia: compara contra los valores de la IA, no contra los de ahora."""
    ya_cambiada = sugerencia(
        estado="cambiada", ninoId="NINO-00263", nucleo="cognitivo", nivel=4, original=ORIGINAL_IA
    )
    assert decisiones.decidir(ya_cambiada, item("aceptada", CAMBIOS_DISTINTOS)) == ("cambiada", ORIGINAL_IA)


# --- Escritura y lectura de la tabla -------------------------------------------------


def test_guardar_escribe_la_fila_de_la_decision(monkeypatch) -> None:
    escritas: list[tuple[str, dict]] = []
    monkeypatch.setattr(decisiones.dynamo, "poner", lambda tabla, fila: escritas.append((tabla, fila)))
    decisiones.guardar(
        CFG,
        SALA_KEY,
        ID_SUG,
        estado="aceptada",
        usuaria_id="EDU-0001",
        validada_en=VALIDADA_EN,
        nino_id="NINO-00253",
        nucleo="lenguaje_comunicacion",
        nivel=9,
    )
    assert escritas == [
        (
            "DecisionesPrueba",
            {
                "sala_key": {"S": SALA_KEY},
                "id_sugerencia": {"S": ID_SUG},
                "estado": {"S": "aceptada"},
                "validada_por": {"S": "EDU-0001"},
                "validada_en": {"S": VALIDADA_EN},
                "nino_id": {"S": "NINO-00253"},
                "nucleo": {"S": "lenguaje_comunicacion"},
                "nivel": {"N": "9"},
            },
        )
    ]


def test_guardar_una_correccion_incluye_el_original(monkeypatch) -> None:
    escritas: list[dict] = []
    monkeypatch.setattr(decisiones.dynamo, "poner", lambda _tabla, fila: escritas.append(fila))
    decisiones.guardar(
        CFG,
        SALA_KEY,
        ID_SUG,
        estado="cambiada",
        usuaria_id="EDU-0001",
        validada_en=VALIDADA_EN,
        nino_id="NINO-00263",
        nucleo="cognitivo",
        nivel=4,
        original=ORIGINAL_IA,
    )
    assert escritas[0]["nino_id"] == {"S": "NINO-00263"}
    assert escritas[0]["nivel"] == {"N": "4"}
    assert escritas[0]["original"] == {
        "M": {"nino_id": {"S": "NINO-00253"}, "nucleo": {"S": "lenguaje_comunicacion"}, "nivel": {"N": "9"}}
    }


def test_guardar_no_acepta_pendiente(monkeypatch) -> None:
    monkeypatch.setattr(decisiones.dynamo, "poner", sin_aws("dynamo.poner"))
    with pytest.raises(ValueError):
        decisiones.guardar(CFG, SALA_KEY, ID_SUG, estado="pendiente", usuaria_id="EDU-0001", validada_en=VALIDADA_EN)


def test_borrar_usa_la_clave_de_la_sala(monkeypatch) -> None:
    borradas: list[tuple[str, dict]] = []
    monkeypatch.setattr(decisiones.dynamo, "borrar", lambda tabla, clave: borradas.append((tabla, clave)))
    decisiones.borrar(CFG, SALA_KEY, ID_SUG)
    assert borradas == [("DecisionesPrueba", {"sala_key": {"S": SALA_KEY}, "id_sugerencia": {"S": ID_SUG}})]


def test_leer_por_sala_consulta_por_sala_key_y_desanida(monkeypatch) -> None:
    consultas: list[dict] = []

    def _consultar_todo(tabla: str, **parametros: object) -> list[dict]:
        consultas.append({"tabla": tabla, **parametros})
        return [
            {
                "sala_key": {"S": SALA_KEY},
                "id_sugerencia": {"S": ID_SUG},
                "estado": {"S": "cambiada"},
                "validada_por": {"S": "EDU-0001"},
                "validada_en": {"S": VALIDADA_EN},
                "nino_id": {"S": "NINO-00263"},
                "nivel": {"N": "4"},
                "original": {"M": {"nino_id": {"S": "NINO-00253"}, "nivel": {"N": "9"}}},
            }
        ]

    monkeypatch.setattr(decisiones.dynamo, "consultar_todo", _consultar_todo)
    filas = decisiones.leer_por_sala(CFG, SALA_KEY)
    assert consultas == [
        {
            "tabla": "DecisionesPrueba",
            "KeyConditionExpression": "sala_key = :sk",
            "ExpressionAttributeValues": {":sk": {"S": SALA_KEY}},
        }
    ]
    assert filas[ID_SUG]["estado"] == "cambiada"
    assert filas[ID_SUG]["nivel"] == 4
    assert filas[ID_SUG]["original"] == {"nino_id": "NINO-00253", "nivel": 9}


# --- La sugerencia que se lee de Observaciones ---------------------------------------


def test_leer_sugerencia_usa_el_id_de_captura_del_id_de_la_observacion(monkeypatch) -> None:
    claves: list[tuple[str, dict]] = []

    def _obtener(tabla: str, clave: dict) -> dict:
        claves.append((tabla, clave))
        return {"origen": {"S": "app"}, "id_obs": {"S": ID_SUG}}

    monkeypatch.setattr(decisiones.dynamo, "obtener", _obtener)
    monkeypatch.setattr(decisiones.mapeo, "a_sugerencia", lambda _item: sugerencia())
    assert decisiones.leer_sugerencia(CFG, ID_SUG) == sugerencia()
    assert claves == [("ObservacionesPrueba", {"id_captura": {"S": ID_CAPTURA}, "id_obs": {"S": ID_SUG}})]


def test_leer_sugerencia_descarta_los_ids_del_dataset(monkeypatch) -> None:
    monkeypatch.setattr(decisiones.dynamo, "obtener", sin_aws("dynamo.obtener"))
    assert decisiones.id_captura_de(ID_DATASET) is None
    assert decisiones.leer_sugerencia(CFG, ID_DATASET) is None


def test_leer_sugerencia_descarta_las_observaciones_del_dataset(monkeypatch) -> None:
    monkeypatch.setattr(decisiones.dynamo, "obtener", lambda _tabla, _clave: {"origen": {"S": "dataset"}})
    assert decisiones.leer_sugerencia(CFG, ID_SUG) is None


def test_leer_sugerencia_sin_observacion(monkeypatch) -> None:
    monkeypatch.setattr(decisiones.dynamo, "obtener", lambda _tabla, _clave: None)
    assert decisiones.leer_sugerencia(CFG, ID_SUG) is None


# --- La decisión guardada, puesta sobre la sugerencia --------------------------------


def test_aplicar_una_aceptada() -> None:
    decision = {"estado": "aceptada", "validada_por": "EDU-0001", "validada_en": VALIDADA_EN}
    aplicada = decisiones.aplicar(sugerencia(), decision)
    assert (aplicada.estado, aplicada.validadaPor, aplicada.validadaEn) == ("aceptada", "EDU-0001", VALIDADA_EN)
    assert aplicada.original is None


def test_aplicar_una_cambiada_pisa_los_valores_y_deja_el_original() -> None:
    decision = {
        "estado": "cambiada",
        "validada_por": "EDU-0001",
        "validada_en": VALIDADA_EN,
        "nino_id": "NINO-00263",
        "nucleo": "cognitivo",
        "nivel": 4,
        "original": {"nino_id": "NINO-00253", "nucleo": "lenguaje_comunicacion", "nivel": 9},
    }
    aplicada = decisiones.aplicar(sugerencia(), decision)
    assert (aplicada.ninoId, aplicada.nucleo, aplicada.nivel) == ("NINO-00263", "cognitivo", 4)
    assert aplicada.original == ORIGINAL_IA


def test_aplicar_acepta_el_original_con_los_nombres_de_contratos() -> None:
    """Se escribe el mapa `original` del spec, pero se leen también los `orig_*`."""
    decision = {
        "estado": "cambiada",
        "validada_por": "EDU-0001",
        "validada_en": VALIDADA_EN,
        "nino_id": "NINO-00263",
        "orig_nino_id": "NINO-00253",
        "orig_nucleo": "lenguaje_comunicacion",
        "orig_nivel": 9,
    }
    assert decisiones.aplicar(sugerencia(), decision).original == ORIGINAL_IA


def test_aplicar_una_descartada() -> None:
    decision = {"estado": "descartada", "validada_por": "EDU-0001", "validada_en": VALIDADA_EN}
    assert decisiones.aplicar(sugerencia(), decision).estado == "descartada"


def test_aplicar_no_borra_el_nino_que_puso_la_regla_5() -> None:
    decision = {"estado": "aceptada", "validada_por": "EDU-0001", "validada_en": VALIDADA_EN, "nino_id": None}
    aplicada = decisiones.aplicar(sugerencia(ninoId="NINO-00346"), decision)
    assert aplicada.ninoId == "NINO-00346"


def test_aplicar_ignora_una_fila_sin_estado_valido() -> None:
    assert decisiones.aplicar(sugerencia(), {"estado": "pendiente"}) == sugerencia()
