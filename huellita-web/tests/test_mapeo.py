"""Pruebas de las reglas puras de `mapeo.py`, con los volcados reales del dataset.

La referencia de las reglas 1, 2 y 4 es `huellita-formato-mejorado/data/semilla.json`: si el
BFF y el modo local no calzan, la demo muestra dos cosas distintas.
"""
from __future__ import annotations

from datetime import datetime

import pytest

from huellita_api import mapeo
from huellita_api.config import cargar_config
from huellita_api.modelos import NUCLEOS

from conftest import ENTORNO_PRUEBA, FECHA_DEMO

MOMENTO = datetime.fromisoformat("2026-10-15T14:30:00-03:00")


def sin_nulos(modelo) -> dict:
    return modelo.model_dump(exclude_none=True)


def observaciones(fixtures: dict, origen: str) -> list[dict]:
    todas = fixtures["observaciones_sga"] + fixtures["observaciones_sgb"]
    return [item for item in todas if item.get("origen", {}).get("S") == origen]


def por_id(items: list[dict], clave: str = "id") -> dict[str, dict]:
    return {item[clave]: item for item in items}


# --- desanidar -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ({"S": "hola"}, "hola"),
        ({"N": "6"}, 6),
        ({"N": "1.5"}, 1.5),
        ({"BOOL": True}, True),
        ({"NULL": True}, None),
        ({"L": []}, []),
        ({"L": [{"S": "a"}, {"N": "2"}]}, ["a", 2]),
        ({"M": {"nivel": {"N": "4"}, "dominio": {"S": "cognitivo"}}}, {"nivel": 4, "dominio": "cognitivo"}),
        ({"B": b"\x00"}, None),
        ({}, None),
        ("no es un atributo", None),
    ],
)
def test_desanidar(valor, esperado) -> None:
    assert mapeo.desanidar(valor) == esperado


def test_desanidar_anida_listas_de_mapas() -> None:
    valor = {"L": [{"M": {"score": {"N": "77"}, "nombre": {"S": "Martina R."}}}]}
    assert mapeo.desanidar(valor) == [{"score": 77, "nombre": "Martina R."}]


# --- criterios compartidos con el modo local -------------------------------------------


@pytest.mark.parametrize(
    ("nombre", "esperado"),
    [
        ("Martina M.", ("Martina", "M.")),
        ("Martina R.", ("Martina", "R.")),
        ("Nayara", ("Nayara", "")),
        ("  Joaquín  ", ("Joaquín", "")),
        ("Sofía A", ("Sofía A", "")),
        ("", ("", "")),
    ],
)
def test_separar_nombre(nombre, esperado) -> None:
    assert mapeo.separar_nombre(nombre) == esperado


@pytest.mark.parametrize(
    ("nacimiento", "hoy", "meses"),
    [
        ("2024-10-01", "2026-10-15", 24),
        ("2024-10-16", "2026-10-15", 23),
        ("2026-10-15", "2026-10-15", 0),
        ("2027-01-01", "2026-10-15", 0),
    ],
)
def test_edad_meses(nacimiento, hoy, meses) -> None:
    assert mapeo.edad_meses(nacimiento, hoy) == meses


@pytest.mark.parametrize(
    ("meses", "nivel"),
    [
        (0, "Sala Cuna Menor"),
        (11, "Sala Cuna Menor"),
        (12, "Sala Cuna Mayor"),
        (23, "Sala Cuna Mayor"),
        (24, "Medio Menor"),
        (35, "Medio Menor"),
        (36, "Medio Mayor"),
        (48, "Transición 1"),
        (60, "Transición 2"),
        (200, "Transición 2"),
    ],
)
def test_nivel_educativo(meses, nivel) -> None:
    assert mapeo.nivel_educativo(meses) == nivel


@pytest.mark.parametrize(
    ("valores", "esperado"),
    [([5], 5), ([1, 2], 1), ([2, 1], 1), ([3, 1, 2], 2), ([4, 1, 3, 2], 2)],
)
def test_mediana_baja(valores, esperado) -> None:
    assert mapeo.mediana_baja(valores) == esperado


def test_nombre_sala() -> None:
    assert mapeo.nombre_sala("SG-A") == "Sala A"
    assert mapeo.nombre_sala("SG-B") == "Sala B"


def test_clave_orden_ignora_tildes_y_mayusculas() -> None:
    assert sorted(["Álvaro", "alba", "Benjamín"], key=mapeo.clave_orden) == ["alba", "Álvaro", "Benjamín"]


# --- regla 1: jardín y salas ------------------------------------------------------------


def test_a_jardin_con_el_volcado_real(fixtures: dict) -> None:
    jardin = mapeo.a_jardin(fixtures["jardin"])
    assert sin_nulos(jardin) == {
        "id": "JAR-0001",
        "nombre": "Jardín Sintético Sendero Azul",
        "comuna": "Arica",
        "region": "Arica y Parinacota",
    }


def test_a_jardin_sin_campos() -> None:
    jardin = mapeo.a_jardin({})
    assert (jardin.id, jardin.nombre, jardin.comuna, jardin.region) == ("", "", "", "")


def test_a_salas_calza_con_la_semilla(fixtures: dict, semilla: dict, cfg) -> None:
    ninos = mapeo.a_ninos(fixtures["ninos"])
    salas = mapeo.a_salas(fixtures["jardin"], cfg, ninos, FECHA_DEMO)
    assert [sin_nulos(sala) for sala in salas] == semilla["salas"]


def test_a_salas_respeta_el_orden_de_la_config_y_lo_que_tiene_el_jardin(fixtures: dict) -> None:
    cfg = cargar_config({**ENTORNO_PRUEBA, "SALAS_DEMO": "SG-B,SG-A,SG-Z"})
    ninos = mapeo.a_ninos(fixtures["ninos"])
    salas = mapeo.a_salas(fixtures["jardin"], cfg, ninos, FECHA_DEMO)
    assert [sala.id for sala in salas] == ["SG-B", "SG-A"]


def test_a_salas_sin_ninos_usa_el_nivel_mas_bajo(fixtures: dict, cfg) -> None:
    salas = mapeo.a_salas(fixtures["jardin"], cfg, [], FECHA_DEMO)
    assert [sala.nivelEducativo for sala in salas] == [mapeo.NIVEL_SIN_NINOS] * 2


def test_a_salas_sin_lista_de_salas_en_el_jardin(cfg) -> None:
    salas = mapeo.a_salas({"id_jardin": {"S": "JAR-0001"}}, cfg, [], FECHA_DEMO)
    assert [sala.id for sala in salas] == ["SG-A", "SG-B"]


# --- regla 2: niños ---------------------------------------------------------------------


def test_a_ninos_calza_con_la_semilla(fixtures: dict, semilla: dict) -> None:
    ninos = mapeo.a_ninos(fixtures["ninos"])
    for sala_id in ("SG-A", "SG-B"):
        de_la_sala = [sin_nulos(nino) for nino in ninos if nino.salaId == sala_id]
        assert de_la_sala == [nino for nino in semilla["ninos"] if nino["salaId"] == sala_id]


def test_a_ninos_separa_homonimos(fixtures: dict) -> None:
    ninos = {nino.id: nino for nino in mapeo.a_ninos(fixtures["ninos"])}
    assert (ninos["NINO-00237"].nombre, ninos["NINO-00237"].apellidoInicial) == ("Martina", "M.")
    assert (ninos["NINO-00263"].nombre, ninos["NINO-00263"].apellidoInicial) == ("Martina", "R.")
    assert (ninos["NINO-00487"].nombre, ninos["NINO-00487"].apellidoInicial) == ("Nayara", "")


def test_a_ninos_deja_fuera_a_los_que_no_tienen_nombre() -> None:
    items = [
        {"id_nino": {"S": "NINO-1"}, "nombre": {"S": "Ana"}, "sala_grupo": {"S": "SG-A"}},
        {"id_nino": {"S": "NINO-2"}, "sala_grupo": {"S": "SG-A"}},
        {"id_nino": {"S": "NINO-3"}, "nombre": {"S": ""}, "sala_grupo": {"S": "SG-A"}},
    ]
    assert [nino.id for nino in mapeo.a_ninos(items)] == ["NINO-1"]


def test_a_nino_sin_campos_y_con_numeros() -> None:
    nino = mapeo.a_nino({"id_nino": {"S": "NINO-9"}, "nombre": {"S": "Ana"}, "ultimo_nivel": {"N": "6"}})
    assert sin_nulos(nino) == {
        "id": "NINO-9",
        "nombre": "Ana",
        "apellidoInicial": "",
        "fechaNacimiento": "",
        "salaId": "",
        "activo": True,
    }


# --- evidencias -------------------------------------------------------------------------


def test_a_evidencia_captura() -> None:
    fila = {
        "id_captura": {"S": "CAP-1"},
        "sala_key": {"S": "JAR-0001#SG-A"},
        "sala_grupo": {"S": "SG-A"},
        "autor_id": {"S": "EDU-0001"},
        "creada_en": {"S": "2026-10-15T14:05:57-03:00"},
        "formato": {"S": "audio"},
        "nino_id_sugerido": {"S": "NINO-00487"},
        "texto_extraido": {"S": "Nayara apiló cinco cubos"},
    }
    assert sin_nulos(mapeo.a_evidencia_captura(fila, "procesando")) == {
        "id": "CAP-1",
        "salaId": "SG-A",
        "autorId": "EDU-0001",
        "creadaEn": "2026-10-15T14:05:57-03:00",
        "formato": "audio",
        "ninoIdSugerido": "NINO-00487",
        "textoExtraido": "Nayara apiló cinco cubos",
        "estado": "procesando",
    }


def test_a_evidencia_captura_sin_campos_ni_formato_conocido() -> None:
    evidencia = mapeo.a_evidencia_captura({"formato": {"S": "video"}}, "error")
    assert sin_nulos(evidencia) == {
        "id": "",
        "salaId": "",
        "autorId": "",
        "creadaEn": "",
        "formato": "texto",
        "estado": "error",
    }


def test_a_evidencia_registro_con_los_volcados_reales(fixtures: dict) -> None:
    registros = {item["id_captura"]["S"]: item for item in fixtures["registros_sga"]}
    manual = mapeo.a_evidencia_registro(registros["CAP-01M503FN5942S3MNAFA14C07AQ"], "lista")
    audio = mapeo.a_evidencia_registro(registros["CAP-01M508E1WXXYXW3KAP0S99M9Z5"], "lista")
    assert sin_nulos(manual) == {
        "id": "CAP-01M503FN5942S3MNAFA14C07AQ",
        "salaId": "SG-A",
        "autorId": "EDU-0001",
        "creadaEn": "2026-10-15T12:39:27-03:00",
        "formato": "texto",
        "estado": "lista",
    }
    assert audio.formato == "audio"


@pytest.mark.parametrize(
    ("tipo", "formato"),
    [("audio", "audio"), ("foto", "foto"), ("manual", "texto"), (None, "texto")],
)
def test_a_evidencia_registro_traduce_el_tipo(tipo, formato) -> None:
    item = {"id_captura": {"S": "CAP-1"}} | ({"tipo": {"S": tipo}} if tipo else {})
    assert mapeo.a_evidencia_registro(item, "procesando").formato == formato


def test_registros_de_una_sala_sin_capturas(fixtures: dict) -> None:
    """`registros_sgb` viene vacío: una sala puede no tener ninguna captura."""
    assert fixtures["registros_sgb"] == []
    assert [mapeo.a_evidencia_registro(item, "lista") for item in fixtures["registros_sgb"]] == []


def test_a_evidencia_observacion_de_una_captura_sin_fila(fixtures: dict) -> None:
    item = next(
        o
        for o in fixtures["observaciones_sga"]
        if o["id_captura"]["S"] == "CAP-01M50AKPA2BHDCXSJATACZ6N3W"
    )
    assert sin_nulos(mapeo.a_evidencia_observacion(item)) == {
        "id": "CAP-01M50AKPA2BHDCXSJATACZ6N3W",
        "salaId": "SG-A",
        "autorId": "EDU-0001",
        "creadaEn": "2026-10-15T14:44:26-03:00",
        "formato": "audio",
        "textoExtraido": "Hola, Agustín, hoy día levantó una torre.",
        "estado": "lista",
    }


def test_a_evidencia_observacion_sin_audio_ni_hora() -> None:
    item = {
        "id_captura": {"S": "CAP-2"},
        "sala_grupo": {"S": "SG-A"},
        "fecha": {"S": "2026-10-15"},
        "texto_literal": {"S": "Hoy bajó la asistencia."},
    }
    evidencia = mapeo.a_evidencia_observacion(item)
    assert (evidencia.formato, evidencia.creadaEn) == ("texto", "2026-10-15T12:00:00-03:00")


# --- regla 4: historial ------------------------------------------------------------------


def test_historial_calza_con_la_semilla(fixtures: dict, semilla: dict) -> None:
    del_dataset = observaciones(fixtures, "dataset")
    assert len(del_dataset) == 155
    evidencias = por_id(semilla["evidencias"])
    sugerencias = por_id(semilla["sugerencias"])
    for item in del_dataset:
        evidencia = mapeo.a_evidencia_historial(item)
        assert sin_nulos(evidencia) == evidencias[evidencia.id]
        propias = mapeo.a_sugerencias_historial(item)
        assert propias, f"{evidencia.id} se quedó sin sugerencias"
        for sugerencia in propias:
            assert sin_nulos(sugerencia) == sugerencias[sugerencia.id]


def test_historial_una_sugerencia_por_dominio(fixtures: dict) -> None:
    item = next(o for o in fixtures["observaciones_sga"] if o["id_obs"]["S"] == "OBS-0000042")
    sugerencias = mapeo.a_sugerencias_historial(item)
    assert [s.id for s in sugerencias] == ["OBS-0000042~cognitivo", "OBS-0000042~socioemocional"]
    assert sugerencias[0].cita == " ".join(
        [
            "Busca con la mirada o la mano un objeto que quedó parcialmente oculto.",
            "Anticipa una acción de una rutina conocida mediante movimiento, mirada o vocalización.",
        ]
    )
    assert (sugerencias[0].estado, sugerencias[0].validadaPor) == ("aceptada", "EDU-0001")
    assert sugerencias[0].validadaEn == "2025-01-03T12:00:00-03:00"


def test_historial_sin_nivel_toma_el_mayor_del_dominio() -> None:
    item = {
        "id_obs": {"S": "OBS-9"},
        "sala_grupo": {"S": "SG-A"},
        "id_nino": {"S": "NINO-1"},
        "id_educadora": {"S": "EDU-0001"},
        "fecha": {"S": "2025-01-03"},
        "manifestaciones": {
            "L": [
                {"M": {"dominio": {"S": "cognitivo"}, "nivel": {"N": "3"}, "texto_observable": {"S": "a"}}},
                {"M": {"dominio": {"S": "cognitivo"}, "nivel": {"N": "5"}, "texto_observable": {"S": "b"}}},
                {"M": {"dominio": {"S": "ninguno"}, "nivel": {"N": "9"}, "texto_observable": {"S": "c"}}},
            ]
        },
    }
    sugerencias = mapeo.a_sugerencias_historial(item)
    assert [(s.nucleo, s.nivel, s.conducta, s.cita) for s in sugerencias] == [("cognitivo", 5, "a", "a b")]


def test_historial_sin_manifestaciones_no_sugiere_nada() -> None:
    item = {"id_obs": {"S": "OBS-9"}, "fecha": {"S": "2025-01-03"}, "manifestaciones": {"L": []}}
    assert mapeo.a_sugerencias_historial(item) == []
    assert mapeo.a_evidencia_historial(item).creadaEn == "2025-01-03T12:00:00-03:00"


# --- regla 5: sugerencias de la app -----------------------------------------------------


def test_sugerencia_particular_con_los_datos_de_la_manifestacion(fixtures: dict) -> None:
    item = next(
        o
        for o in fixtures["observaciones_sga"]
        if o["id_obs"]["S"] == "CAP-01M503FN5942S3MNAFA14C07AQ-p0-0"
    )
    assert sin_nulos(mapeo.a_sugerencia(item)) == {
        "id": "CAP-01M503FN5942S3MNAFA14C07AQ-p0-0",
        "evidenciaId": "CAP-01M503FN5942S3MNAFA14C07AQ",
        "salaId": "SG-A",
        "tipo": "evaluacion",
        "ninoId": "NINO-00253",
        "nucleo": "lenguaje_comunicacion",
        "nivel": 9,
        "conducta": (
            "Produce combinaciones de tres o más palabras, aproximaciones o señas para relatar, "
            "pedir o comentar."
        ),
        "cita": "Pedro apilo tres bloques y despues conto 'uno, dos, tres' senalando cada uno.",
        "certeza": "media",
        "estado": "pendiente",
    }


def test_sugerencia_no_identificado_con_candidatos(fixtures: dict) -> None:
    item = next(
        o
        for o in fixtures["observaciones_sga"]
        if o["id_obs"]["S"] == "CAP-01M508E1WXXYXW3KAP0S99M9Z5-p0-0"
    )
    assert sin_nulos(mapeo.a_sugerencia(item)) == {
        "id": "CAP-01M508E1WXXYXW3KAP0S99M9Z5-p0-0",
        "evidenciaId": "CAP-01M508E1WXXYXW3KAP0S99M9Z5",
        "salaId": "SG-A",
        "tipo": "evaluacion",
        "nombreDetectado": "Martina R.",
        "cita": "Hola, Agustín, hoy día levantó una torre.",
        "certeza": "baja",
        "estado": "pendiente",
    }


def test_sugerencia_general_es_nota_de_sala(fixtures: dict) -> None:
    item = next(
        o
        for o in fixtures["observaciones_sga"]
        if o["id_obs"]["S"] == "CAP-01M50AJR5TDANWWKDXZWD448KJ-p0-2"
    )
    sugerencia = mapeo.a_sugerencia(item)
    assert (sugerencia.tipo, sugerencia.certeza, sugerencia.nucleo) == ("nota_sala", "alta", None)
    assert sugerencia.cita == "Hoy bajó la asistencia, mucha tos."


def test_sugerencia_elige_la_manifestacion_de_mayor_certeza() -> None:
    item = {
        "id_obs": {"S": "CAP-9-p0-0"},
        "id_captura": {"S": "CAP-9"},
        "sala_grupo": {"S": "SG-A"},
        "id_nino": {"S": "NINO-1"},
        "tipo": {"S": "PARTICULAR"},
        "certeza": {"S": "media"},
        "texto_literal": {"S": "Armó una torre."},
        "manifestaciones": {
            "L": [
                {
                    "M": {
                        "dominio": {"S": "motor_fino"},
                        "nivel": {"N": "6"},
                        "texto_observable": {"S": "Apila dos bloques"},
                        "certeza": {"S": "baja"},
                    }
                },
                {
                    "M": {
                        "dominio": {"S": "cognitivo"},
                        "nivel": {"N": "8"},
                        "texto_observable": {"S": "Clasifica objetos"},
                        "certeza": {"S": "alta"},
                    }
                },
            ]
        },
    }
    sugerencia = mapeo.a_sugerencia(item)
    assert (sugerencia.nucleo, sugerencia.nivel, sugerencia.conducta) == (
        "cognitivo",
        8,
        "Clasifica objetos",
    )


def test_sugerencia_sin_nivel_propio_usa_el_de_la_manifestacion() -> None:
    item = {
        "id_obs": {"S": "CAP-9-p0-0"},
        "tipo": {"S": "PARTICULAR"},
        "nivel": {"N": "12"},
        "manifestaciones": {
            "L": [{"M": {"dominio": {"S": "cognitivo"}, "nivel": {"N": "7"}, "texto_observable": {"S": "x"}}}]
        },
    }
    assert mapeo.a_sugerencia(item).nivel == 7


def test_sugerencia_con_dominio_que_no_conocemos() -> None:
    item = {
        "id_obs": {"S": "CAP-9-p0-0"},
        "tipo": {"S": "PARTICULAR"},
        "manifestaciones": {"L": [{"M": {"dominio": {"S": "musical"}, "nivel": {"N": "7"}}}]},
    }
    sugerencia = mapeo.a_sugerencia(item)
    assert (sugerencia.nucleo, sugerencia.nivel) == (None, 7)


@pytest.mark.parametrize(
    ("extra", "conducta"),
    [
        (
            {"evaluabilidad": {"S": "NO_EVALUABLE"}, "motivo_no_evaluable": {"S": "CONDUCTA_ADULTO"}},
            mapeo.MOTIVOS_NO_EVALUABLE["CONDUCTA_ADULTO"],
        ),
        ({"evaluabilidad": {"S": "NO_EVALUABLE"}}, mapeo.CONDUCTA_SIN_EVALUAR),
        ({"error_evaluacion": {"S": "LLM_SALIDA_INVALIDA"}}, mapeo.CONDUCTA_SIN_EVALUAR),
    ],
)
def test_sugerencia_sin_evaluar_explica_el_motivo(extra, conducta) -> None:
    item = {
        "id_obs": {"S": "CAP-9-p0-0"},
        "tipo": {"S": "PARTICULAR"},
        "nivel": {"N": "7"},
        "texto_literal": {"S": "La tía ordenó la sala."},
        "manifestaciones": {
            "L": [{"M": {"dominio": {"S": "cognitivo"}, "nivel": {"N": "7"}, "texto_observable": {"S": "x"}}}]
        },
        **extra,
    }
    sugerencia = mapeo.a_sugerencia(item)
    assert (sugerencia.tipo, sugerencia.nucleo, sugerencia.nivel) == ("evaluacion", None, None)
    assert sugerencia.conducta == conducta


def test_todas_las_sugerencias_de_la_app_son_validas(fixtures: dict) -> None:
    de_la_app = observaciones(fixtures, "app")
    assert len(de_la_app) == 6
    for item in de_la_app:
        sugerencia = mapeo.a_sugerencia(item)
        assert sugerencia.estado == "pendiente"
        assert sugerencia.nucleo is None or sugerencia.nucleo in NUCLEOS
        assert sugerencia.evidenciaId.startswith("CAP-")


# --- nombreDetectado (DECISIÓN ABIERTA) -------------------------------------------------


def test_nombre_detectado_toma_el_primer_candidato() -> None:
    candidatos = [{"nombre": "Martina R.", "score": 77}, {"nombre": "Rusi", "score": 90}]
    assert mapeo.nombre_detectado(candidatos) == "Martina R."


@pytest.mark.parametrize("candidatos", [[], None, [{"nombre": "Sin puntaje"}], ["basura"]])
def test_nombre_detectado_sin_candidatos_utiles(candidatos) -> None:
    assert mapeo.nombre_detectado(candidatos) is None


def test_nombre_detectado_respeta_el_umbral(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mapeo, "UMBRAL_PUNTAJE_CANDIDATO", 80)
    candidatos = [{"nombre": "Martina R.", "score": 77}, {"nombre": "Rusi", "score": 90}]
    assert mapeo.nombre_detectado(candidatos) == "Rusi"


# --- regla 6 -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("estado", "esperado"),
    [
        ("RECIBIDO", "procesando"),
        ("PROCESANDO", "procesando"),
        ("PROCESADO", "lista"),
        ("SIN_TEXTO", "error"),
        ("ERROR", "error"),
        (None, "procesando"),
        ("CUALQUIERA", "procesando"),
    ],
)
def test_estado_de_registro(estado, esperado) -> None:
    assert mapeo.estado_de_registro(estado) == esperado


def fila(**atributos: str) -> dict:
    base = {"id_captura": "CAP-1", "creada_en": "2026-10-15T14:20:00-03:00", "estado_envio": "enviada"}
    return {clave: {"S": valor} for clave, valor in (base | atributos).items()}


@pytest.mark.parametrize(
    ("atributos", "registro", "esperado"),
    [
        ({"estado_envio": "enviando"}, None, "procesando"),
        ({"estado_envio": "error_envio"}, None, "error"),
        ({}, None, "procesando"),
        ({}, {"estado": {"S": "RECIBIDO"}}, "procesando"),
        ({}, {"estado": {"S": "PROCESADO"}}, "lista"),
        ({}, {"estado": {"S": "SIN_TEXTO"}}, "error"),
        ({"estado_final": "lista"}, None, "lista"),
        ({"estado_final": "error"}, {"estado": {"S": "PROCESADO"}}, "error"),
        ({"estado_final": "cualquiera"}, None, "procesando"),
    ],
)
def test_regla6(atributos, registro, esperado) -> None:
    assert mapeo.regla6(fila(**atributos), registro, MOMENTO, 20) == esperado


def test_regla6_archivada_queda_lista() -> None:
    propia = fila(estado_envio="error_envio") | {"archivada": {"BOOL": True}}
    assert mapeo.regla6(propia, None, MOMENTO, 20) == "lista"


@pytest.mark.parametrize(
    ("creada_en", "esperado"),
    [
        ("2026-10-15T14:10:01-03:00", "procesando"),
        ("2026-10-15T14:10:00-03:00", "procesando"),
        ("2026-10-15T14:09:59-03:00", "error"),
        ("fecha ilegible", "procesando"),
    ],
)
def test_regla6_vence_a_los_veinte_minutos(creada_en, esperado) -> None:
    assert mapeo.regla6(fila(creada_en=creada_en), None, MOMENTO, 20) == esperado


def test_regla6_lo_terminal_no_vence() -> None:
    vieja = fila(creada_en="2026-10-15T10:00:00-03:00")
    assert mapeo.regla6(vieja, {"estado": {"S": "PROCESADO"}}, MOMENTO, 20) == "lista"
