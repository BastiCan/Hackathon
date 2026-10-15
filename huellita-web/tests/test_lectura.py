"""Pruebas de `datos/lectura.py` con el doble de DynamoDB y los volcados reales.

Ninguna prueba sale a la red: el cliente de DynamoDB es un doble y este módulo no habla con
el transcriptor (eso es de `datos/audio.py`, ver `test_audio.py`).
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from huellita_api import errores
from huellita_api.datos import lectura

from conftest import FECHA_DEMO, MOMENTO_DEMO

CAP_TEXTO = "CAP-01M503FN5942S3MNAFA14C07AQ"
CAP_AUDIO = "CAP-01M508E1WXXYXW3KAP0S99M9Z5"
CAP_SIN_REGISTRO = "CAP-01M50AJR5TDANWWKDXZWD448KJ"
CAP_AUDIO_SIN_FILA = "CAP-01M50AKPA2BHDCXSJATACZ6N3W"
SALA_KEY = "JAR-0001#SG-A"


def tablas(fixtures: dict, capturas: list[dict] | None = None, decisiones: list[dict] | None = None) -> dict:
    return {
        "Jardines": [fixtures["jardin"]],
        "Ninos": fixtures["ninos"],
        "Registros": fixtures["registros_sga"] + fixtures["registros_sgb"],
        "Observaciones": fixtures["observaciones_sga"] + fixtures["observaciones_sgb"],
        "Capturas": capturas or [],
        "Decisiones": decisiones or [],
    }


def fila(id_captura: str, **atributos) -> dict:
    """Una fila de Capturas con los atributos del spec (§2)."""
    base = {
        "id_captura": id_captura,
        "sala_key": SALA_KEY,
        "sala_grupo": "SG-A",
        "id_jardin": "JAR-0001",
        "autor_id": "EDU-0001",
        "creada_en": "2026-10-15T14:50:00-03:00",
        "formato": "texto",
        "estado_envio": "enviada",
    }
    return {clave: {"S": valor} for clave, valor in (base | atributos).items()}


def contador() -> dict:
    """El ítem del tope diario: sin `sala_key`, así que no entra al índice `porSala`."""
    return {"id_captura": {"S": f"CONTADOR#{FECHA_DEMO}"}, "total": {"N": "3"}}


def evidencias_por_id(registros) -> dict:
    return {evidencia.id: evidencia for evidencia in registros.evidencias}


def sugerencias_por_id(registros) -> dict:
    return {sugerencia.id: sugerencia for sugerencia in registros.sugerencias}


def valores(actualizacion: dict) -> dict:
    return {
        marcador: next(iter(valor.values()))
        for marcador, valor in actualizacion["ExpressionAttributeValues"].items()
    }


# --- contexto y niños -------------------------------------------------------------------


def test_leer_contexto(fixtures: dict, semilla: dict, cfg, dynamo_falso, reloj_demo) -> None:
    dynamo_falso(tablas(fixtures))
    contexto = lectura.leer_contexto(cfg, reloj_demo)
    assert contexto.jardin.nombre == "Jardín Sintético Sendero Azul"
    assert [sala.model_dump(exclude_none=True) for sala in contexto.salas] == semilla["salas"]
    assert [usuaria.id for usuaria in contexto.usuarias] == ["EDU-0001", "EDU-0002"]


def test_leer_contexto_sin_jardin(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    dynamo_falso({**tablas(fixtures), "Jardines": []})
    with pytest.raises(errores.ErrorApi) as falla:
        lectura.leer_contexto(cfg, reloj_demo)
    assert falla.value.codigo == "no_encontrado"


def test_leer_ninos_calza_con_la_semilla(fixtures: dict, semilla: dict, cfg, dynamo_falso) -> None:
    dynamo_falso(tablas(fixtures))
    ninos = lectura.leer_ninos(cfg, "SG-A")
    assert [nino.model_dump(exclude_none=True) for nino in ninos] == [
        nino for nino in semilla["ninos"] if nino["salaId"] == "SG-A"
    ]


def test_leer_ninos_de_una_sala_sin_niños(fixtures: dict, cfg, dynamo_falso) -> None:
    dynamo_falso(tablas(fixtures))
    assert lectura.leer_ninos(cfg, "SG-Z") == []


def test_leer_ninos_pagina_la_consulta(fixtures: dict, cfg, dynamo_falso) -> None:
    falso = dynamo_falso(tablas(fixtures), tam_pagina=2)
    assert len(lectura.leer_ninos(cfg, "SG-A")) == 13
    assert len(falso.consultas) > 1


def test_leer_nino(fixtures: dict, cfg, dynamo_falso) -> None:
    dynamo_falso(tablas(fixtures))
    nino = lectura.leer_nino(cfg, "NINO-00487")
    assert (nino.nombre, nino.salaId) == ("Nayara", "SG-A")


@pytest.mark.parametrize("id_nino", ["NINO-99999", ""])
def test_leer_nino_que_no_esta(fixtures: dict, cfg, dynamo_falso, id_nino) -> None:
    dynamo_falso(tablas(fixtures))
    with pytest.raises(errores.ErrorApi) as falla:
        lectura.leer_nino(cfg, id_nino)
    assert falla.value.codigo == "no_encontrado"


# --- registros: las cuatro fuentes ------------------------------------------------------


def test_registros_junta_historial_registros_y_observaciones(
    fixtures: dict, cfg, dynamo_falso, reloj_demo
) -> None:
    dynamo_falso(tablas(fixtures))
    registros = lectura.leer_registros(cfg, "SG-A", reloj_demo)
    evidencias = evidencias_por_id(registros)

    del_historial = [e for e in registros.evidencias if e.id.startswith("OBS-")]
    de_capturas = [e for e in registros.evidencias if e.id.startswith("CAP-")]
    assert len(del_historial) == 82
    assert {e.id for e in de_capturas} == {CAP_TEXTO, CAP_AUDIO, CAP_SIN_REGISTRO, CAP_AUDIO_SIN_FILA}
    # Registros dice PROCESADO en las tres que llegaron a integra-procesador.
    assert evidencias[CAP_TEXTO].estado == "lista"
    assert evidencias[CAP_TEXTO].formato == "texto"
    assert evidencias[CAP_AUDIO].formato == "audio"
    # La captura que no está en Registros se arma desde su observación (regla 5).
    assert evidencias[CAP_SIN_REGISTRO].estado == "lista"
    assert evidencias[CAP_SIN_REGISTRO].autorId == "EDU-0001"
    assert evidencias[CAP_AUDIO_SIN_FILA].formato == "audio"


def test_registros_ordena_las_evidencias_por_fecha(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    dynamo_falso(tablas(fixtures))
    registros = lectura.leer_registros(cfg, "SG-A", reloj_demo)
    fechas = [evidencia.creadaEn for evidencia in registros.evidencias]
    assert fechas == sorted(fechas)
    assert registros.evidencias[-1].id == CAP_AUDIO_SIN_FILA


def test_registros_rellena_el_texto_desde_la_observacion(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    dynamo_falso(tablas(fixtures))
    evidencias = evidencias_por_id(lectura.leer_registros(cfg, "SG-A", reloj_demo))
    assert evidencias[CAP_TEXTO].textoExtraido == (
        "Pedro apilo tres bloques y despues conto 'uno, dos, tres' senalando cada uno."
    )
    assert evidencias[CAP_AUDIO].textoExtraido == "Hola, Agustín, hoy día levantó una torre."


def test_registros_trae_las_sugerencias_de_la_app_y_del_historial(
    fixtures: dict, cfg, dynamo_falso, reloj_demo
) -> None:
    dynamo_falso(tablas(fixtures))
    registros = lectura.leer_registros(cfg, "SG-A", reloj_demo)
    sugerencias = sugerencias_por_id(registros)
    de_la_app = [s for s in registros.sugerencias if s.evidenciaId.startswith("CAP-")]
    assert len(de_la_app) == 6
    assert all(s.estado == "pendiente" for s in de_la_app)
    assert sugerencias["OBS-0000042~cognitivo"].estado == "aceptada"
    assert [(s.evidenciaId, s.id) for s in registros.sugerencias] == sorted(
        (s.evidenciaId, s.id) for s in registros.sugerencias
    )


def test_registros_de_una_sala_sin_capturas(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    dynamo_falso(tablas(fixtures))
    registros = lectura.leer_registros(cfg, "SG-B", reloj_demo)
    assert len(registros.evidencias) == 73
    assert all(evidencia.id.startswith("OBS-") for evidencia in registros.evidencias)
    assert all(sugerencia.estado == "aceptada" for sugerencia in registros.sugerencias)


# --- regla 6: estado de las capturas propias --------------------------------------------


def test_captura_propia_con_registro_procesado_queda_lista_y_se_guarda(
    fixtures: dict, cfg, dynamo_falso, reloj_demo
) -> None:
    falso = dynamo_falso(tablas(fixtures, capturas=[fila(CAP_TEXTO)]))
    evidencias = evidencias_por_id(lectura.leer_registros(cfg, "SG-A", reloj_demo))
    assert evidencias[CAP_TEXTO].estado == "lista"
    assert len(falso.actualizaciones) == 1
    guardado = valores(falso.actualizaciones[0])
    assert guardado[":f"] == "lista"
    assert guardado[":t"].startswith("Pedro apilo tres bloques")
    assert falso.actualizaciones[0]["Key"] == {"id_captura": {"S": CAP_TEXTO}}


def test_captura_propia_sin_registro_sigue_procesando(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    falso = dynamo_falso(tablas(fixtures, capturas=[fila("CAP-NUEVA")]))
    evidencias = evidencias_por_id(lectura.leer_registros(cfg, "SG-A", reloj_demo))
    assert evidencias["CAP-NUEVA"].estado == "procesando"
    assert falso.actualizaciones == []


def test_captura_propia_vencida_queda_en_error_sin_guardarlo(fixtures: dict, cfg, dynamo_falso) -> None:
    falso = dynamo_falso(tablas(fixtures, capturas=[fila("CAP-NUEVA")]))
    tarde = MOMENTO_DEMO + timedelta(minutes=30)
    evidencias = evidencias_por_id(lectura.leer_registros(cfg, "SG-A", lambda: tarde))
    assert evidencias["CAP-NUEVA"].estado == "error"
    assert falso.actualizaciones == []


def test_captura_propia_archivada_queda_lista(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    archivada = fila("CAP-NUEVA", estado_envio="error_envio") | {"archivada": {"BOOL": True}}
    falso = dynamo_falso(tablas(fixtures, capturas=[archivada]))
    evidencias = evidencias_por_id(lectura.leer_registros(cfg, "SG-A", reloj_demo))
    assert evidencias["CAP-NUEVA"].estado == "lista"
    assert falso.actualizaciones == []


def test_captura_con_error_de_envio(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    dynamo_falso(tablas(fixtures, capturas=[fila("CAP-NUEVA", estado_envio="error_envio")]))
    evidencias = evidencias_por_id(lectura.leer_registros(cfg, "SG-A", reloj_demo))
    assert evidencias["CAP-NUEVA"].estado == "error"


def test_la_fila_propia_manda_sobre_registros(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    """La misma captura está en Capturas y en Registros: la evidencia sale de la fila."""
    propia = fila(CAP_AUDIO, formato="audio", texto_extraido="transcripción guardada")
    dynamo_falso(tablas(fixtures, capturas=[propia]))
    evidencias = evidencias_por_id(lectura.leer_registros(cfg, "SG-A", reloj_demo))
    assert evidencias[CAP_AUDIO].textoExtraido == "transcripción guardada"
    assert evidencias[CAP_AUDIO].autorId == "EDU-0001"


def test_el_contador_del_dia_no_es_una_evidencia(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    dynamo_falso(tablas(fixtures, capturas=[contador(), fila("CAP-NUEVA")]))
    evidencias = evidencias_por_id(lectura.leer_registros(cfg, "SG-A", reloj_demo))
    assert [id_evidencia for id_evidencia in evidencias if id_evidencia.startswith("CONTADOR")] == []
    assert "CAP-NUEVA" in evidencias


# --- Registros: solo lo que falta -------------------------------------------------------


def test_solo_consulta_registros_de_las_capturas_sin_estado_final(
    fixtures: dict, cfg, dynamo_falso, reloj_demo
) -> None:
    capturas = [
        fila("CAP-PENDIENTE"),
        fila("CAP-CERRADA", estado_final="lista"),
        fila("CAP-ARCHIVADA", estado_final="error"),
    ]
    falso = dynamo_falso(tablas(fixtures, capturas=capturas))
    lectura.leer_registros(cfg, "SG-A", reloj_demo)
    assert falso.claves_pedidas == ["CAP-PENDIENTE"]


def test_sin_capturas_propias_no_hay_lote(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    falso = dynamo_falso(tablas(fixtures))
    lectura.leer_registros(cfg, "SG-A", reloj_demo)
    assert falso.claves_pedidas == []


def test_reintenta_las_claves_sin_procesar(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    capturas = [fila(CAP_TEXTO), fila(CAP_AUDIO, formato="audio")]
    falso = dynamo_falso(tablas(fixtures, capturas=capturas), sin_procesar=1)
    evidencias = evidencias_por_id(lectura.leer_registros(cfg, "SG-A", reloj_demo))
    assert [evidencias[CAP_TEXTO].estado, evidencias[CAP_AUDIO].estado] == ["lista", "lista"]
    assert falso.claves_pedidas == [CAP_TEXTO, CAP_AUDIO, CAP_TEXTO]


# --- regla 5: la nota tomada desde la ficha ---------------------------------------------


def test_nino_sugerido_se_aplica_a_las_no_identificadas(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    propia = fila(CAP_AUDIO, formato="audio", nino_id_sugerido="NINO-00487")
    dynamo_falso(tablas(fixtures, capturas=[propia]))
    sugerencias = sugerencias_por_id(lectura.leer_registros(cfg, "SG-A", reloj_demo))
    no_identificada = sugerencias[f"{CAP_AUDIO}-p0-0"]
    assert no_identificada.ninoId == "NINO-00487"
    assert no_identificada.nombreDetectado == "Martina R."


def test_nino_sugerido_no_pisa_a_quien_ya_tiene_nino(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    propia = fila(CAP_TEXTO, nino_id_sugerido="NINO-00487")
    dynamo_falso(tablas(fixtures, capturas=[propia]))
    sugerencias = sugerencias_por_id(lectura.leer_registros(cfg, "SG-A", reloj_demo))
    assert sugerencias[f"{CAP_TEXTO}-p0-0"].ninoId == "NINO-00253"


# --- regla 7: decisiones ----------------------------------------------------------------


def decision(id_sugerencia: str, **atributos) -> dict:
    base = {
        "sala_key": SALA_KEY,
        "id_sugerencia": id_sugerencia,
        "estado": "aceptada",
        "validada_por": "EDU-0001",
        "validada_en": "2026-10-15T15:10:00-03:00",
    }
    item = {clave: {"S": valor} for clave, valor in (base | atributos).items()}
    return item


def test_las_decisiones_pisan_a_la_ia(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    guardada = decision(f"{CAP_TEXTO}-p0-0")
    dynamo_falso(tablas(fixtures, decisiones=[guardada]))
    sugerencias = sugerencias_por_id(lectura.leer_registros(cfg, "SG-A", reloj_demo))
    decidida = sugerencias[f"{CAP_TEXTO}-p0-0"]
    assert (decidida.estado, decidida.validadaPor) == ("aceptada", "EDU-0001")
    assert decidida.validadaEn == "2026-10-15T15:10:00-03:00"
    assert sugerencias[f"{CAP_AUDIO}-p0-0"].estado == "pendiente"


def test_una_decision_cambiada_trae_el_original(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    guardada = decision(f"{CAP_TEXTO}-p0-0", estado="cambiada", nino_id="NINO-00487", nucleo="motor_fino") | {
        "nivel": {"N": "6"},
        "original": {
            "M": {
                "nino_id": {"S": "NINO-00253"},
                "nucleo": {"S": "lenguaje_comunicacion"},
                "nivel": {"N": "9"},
            }
        },
    }
    dynamo_falso(tablas(fixtures, decisiones=[guardada]))
    sugerencias = sugerencias_por_id(lectura.leer_registros(cfg, "SG-A", reloj_demo))
    decidida = sugerencias[f"{CAP_TEXTO}-p0-0"]
    assert (decidida.estado, decidida.ninoId, decidida.nucleo, decidida.nivel) == (
        "cambiada",
        "NINO-00487",
        "motor_fino",
        6,
    )
    assert decidida.original is not None
    assert decidida.original.model_dump() == {
        "ninoId": "NINO-00253",
        "nucleo": "lenguaje_comunicacion",
        "nivel": 9,
    }


def test_las_decisiones_de_otra_sala_no_se_mezclan(fixtures: dict, cfg, dynamo_falso, reloj_demo) -> None:
    ajena = decision(f"{CAP_TEXTO}-p0-0", sala_key="JAR-0001#SG-B", estado="descartada")
    dynamo_falso(tablas(fixtures, decisiones=[ajena]))
    sugerencias = sugerencias_por_id(lectura.leer_registros(cfg, "SG-A", reloj_demo))
    assert sugerencias[f"{CAP_TEXTO}-p0-0"].estado == "pendiente"


def test_leer_registros_no_habla_con_el_transcriptor(
    fixtures: dict, cfg, dynamo_falso, reloj_demo
) -> None:
    """Las transcripciones las pone al día `datos/audio`; acá solo se lee DynamoDB."""
    audio = fila("CAP-NUEVA", formato="audio", id_trabajo="tr-CAP-NUEVA")
    falso = dynamo_falso(tablas(fixtures, capturas=[audio]))

    evidencias = evidencias_por_id(lectura.leer_registros(cfg, "SG-A", reloj_demo))

    assert evidencias["CAP-NUEVA"].estado == "procesando"
    assert falso.actualizaciones == []
