"""Entrega a ProcesarNota: el audio en capturas/{id}/original/ y texto.json en el bucket de capturas."""
from __future__ import annotations

import pytest

from transcriptor.eventos import handler
from transcriptor.servicio import MetaPendiente

from conftest import CRUDO, trabajo, validar

ID_CAPTURA = "CAP-01JXK5Y8N3Q7W2M9C4R6T1V0ZA"  # formato CAP-<ULID>, el único que acepta ProcesarNota
ID = "tr-" + ID_CAPTURA
TEXTO = "Armó una torre de seis bloques y después ayudó a ordenar."
EVENTO = {"detail": {"TranscriptionJobName": ID, "TranscriptionJobStatus": "COMPLETED"}}


def _hasta_transcripcion(aws, crudo=CRUDO):
    aws.objeto_no_existe(f"resultados/{ID}.json")
    aws.trabajo_existe(trabajo("COMPLETED", id_trabajo=ID))
    aws.objeto(f"transcripciones/{ID}.json", crudo)


def _cierre(aws):
    aws.guarda_resultado(ID)
    aws.borra_audio(ID)


def test_copia_el_audio_y_entrega_texto_json(aws, cliente):
    _hasta_transcripcion(aws)
    aws.meta_existe(ID_CAPTURA)
    aws.copia_audio(ID_CAPTURA, ID)
    aws.entrega_texto(ID_CAPTURA, TEXTO)  # partes[0].archivo = original/audio.webm
    _cierre(aws)
    cuerpo = validar(cliente.get(f"/api/transcripciones/{ID}").json())
    assert cuerpo["estado"] == "completado" and cuerpo["texto_completo"] == TEXTO


def test_evento_copia_el_audio_y_entrega_texto_json(aws):
    _hasta_transcripcion(aws)
    aws.meta_existe(ID_CAPTURA)
    aws.copia_audio(ID_CAPTURA, ID)
    aws.entrega_texto(ID_CAPTURA, TEXTO)
    _cierre(aws)
    assert handler(EVENTO)["procesado"] is True


def test_sin_audio_disponible_entrega_solo_el_texto(aws, cliente):
    _hasta_transcripcion(aws)
    aws.meta_existe(ID_CAPTURA)
    aws.copia_audio(ID_CAPTURA, ID, error=("NoSuchKey", 404))
    aws.entrega_texto(ID_CAPTURA, TEXTO, archivo=None)
    _cierre(aws)
    assert cliente.get(f"/api/transcripciones/{ID}").json()["estado"] == "completado"


def test_error_al_copiar_el_audio_no_entrega_ni_guarda(aws, cliente):
    _hasta_transcripcion(aws)
    aws.meta_existe(ID_CAPTURA)
    aws.copia_audio(ID_CAPTURA, ID, error=("AccessDenied", 403))
    r = cliente.get(f"/api/transcripciones/{ID}")
    assert r.status_code == 502 and r.json()["error"]["codigo"] == "error_proveedor"


def test_no_sobrescribe_un_texto_json_existente(aws, cliente):
    _hasta_transcripcion(aws)
    aws.meta_existe(ID_CAPTURA)
    aws.copia_audio(ID_CAPTURA, ID)
    aws.entrega_texto(ID_CAPTURA, TEXTO, error=("PreconditionFailed", 412))
    _cierre(aws)
    assert cliente.get(f"/api/transcripciones/{ID}").json()["estado"] == "completado"


def test_sin_meta_json_no_copia_ni_entrega_ni_guarda(aws, cliente):
    _hasta_transcripcion(aws)
    aws.meta_no_existe(ID_CAPTURA)
    r = cliente.get(f"/api/transcripciones/{ID}")
    # Devuelve el texto, pero no guarda el resultado: el siguiente GET o reintento vuelve a intentar.
    assert r.status_code == 200 and validar(r.json())["estado"] == "completado"


def test_evento_sin_meta_json_falla_para_que_lambda_reintente(aws):
    _hasta_transcripcion(aws)
    aws.meta_no_existe(ID_CAPTURA)
    with pytest.raises(MetaPendiente):
        handler(EVENTO)


def test_error_al_entregar_no_guarda_el_resultado(aws, cliente):
    _hasta_transcripcion(aws)
    aws.meta_existe(ID_CAPTURA)
    aws.copia_audio(ID_CAPTURA, ID)
    aws.entrega_texto(ID_CAPTURA, TEXTO, error=("AccessDenied", 403))
    r = cliente.get(f"/api/transcripciones/{ID}")
    assert r.status_code == 502 and r.json()["error"]["codigo"] == "error_proveedor"


def test_trabajo_fallido_no_entrega(aws, cliente):
    aws.objeto_no_existe(f"resultados/{ID}.json")
    aws.trabajo_existe(trabajo("FAILED", id_trabajo=ID, FailureReason="Motivo de prueba"))
    _cierre(aws)
    assert cliente.get(f"/api/transcripciones/{ID}").json()["estado"] == "fallido"


def test_audio_sin_voz_no_entrega(aws, cliente):
    _hasta_transcripcion(aws, {"results": {"transcripts": [{"transcript": ""}], "items": []}})
    _cierre(aws)
    assert cliente.get(f"/api/transcripciones/{ID}").json()["texto_completo"] == ""


def test_id_sin_formato_cap_ulid_no_entrega(aws, cliente):
    # CAP-000012 no es CAP-<ULID>: ProcesarNota lo ignoraría, así que no se copia ni se escribe nada.
    aws.objeto_no_existe("resultados/tr-CAP-000012.json")
    aws.trabajo_existe(trabajo("COMPLETED"))
    aws.objeto("transcripciones/tr-CAP-000012.json", CRUDO)
    aws.guarda_resultado()
    aws.borra_audio()
    assert cliente.get("/api/transcripciones/tr-CAP-000012").status_code == 200