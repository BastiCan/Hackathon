"""Handler de EventBridge con S3 y Transcribe simulados."""
from __future__ import annotations

from transcriptor.eventos import handler

from conftest import CRUDO, ID, ejemplo, trabajo


def _evento(nombre: str = ID, estado: str = "COMPLETED") -> dict:
    return {
        "version": "0",
        "id": "evento-prueba",
        "detail-type": "Transcribe Job State Change",
        "source": "aws.transcribe",
        "account": "111122223333",
        "time": "2026-10-15T14:02:38Z",
        "region": "us-east-1",
        "resources": [],
        "detail": {"TranscriptionJobName": nombre, "TranscriptionJobStatus": estado},
    }


def test_evento_guarda_el_resultado(aws):
    aws.objeto_no_existe(f"resultados/{ID}.json")
    aws.trabajo_existe(trabajo("COMPLETED"))
    aws.objeto(f"transcripciones/{ID}.json", CRUDO)
    aws.guarda_resultado()
    aws.borra_audio()
    assert handler(_evento()) == {"procesado": True, "id_trabajo": ID, "estado": "completado"}


def test_evento_repetido_no_rehace_el_trabajo(aws):
    aws.objeto(f"resultados/{ID}.json", ejemplo("completado"))
    assert handler(_evento())["procesado"] is True


def test_evento_de_otro_prefijo_se_ignora(aws):
    assert handler(_evento("otro-trabajo")) == {"procesado": False, "id_trabajo": "otro-trabajo"}


def test_evento_sin_trabajo(aws):
    assert handler({"detail": {}}) == {"procesado": False}