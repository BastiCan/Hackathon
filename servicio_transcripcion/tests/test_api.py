"""API con S3 y Transcribe simulados."""
from __future__ import annotations

import base64
from dataclasses import replace

import pytest
from botocore.exceptions import ReadTimeoutError

from conftest import BUCKET, CRUDO, ID, WEBM, ejemplo, trabajo, validar

B64 = base64.b64encode(WEBM).decode()


def _post(cliente, **cambios):
    return cliente.post("/api/transcripciones/audio", json={"id_captura": "CAP-000012", "audio_base64": B64, **cambios})


def _parametros_inicio(idioma: str = "es-US") -> dict:
    return {
        "TranscriptionJobName": ID,
        "LanguageCode": idioma,
        "Media": {"MediaFileUri": f"s3://{BUCKET}/audio/{ID}.webm"},
        "OutputBucketName": BUCKET,
        "OutputKey": f"transcripciones/{ID}.json",
    }


def test_post_inicia_transcripcion(aws, cliente):
    aws.trabajo_no_existe()
    aws.sube_audio()
    aws.transcribe.add_response("start_transcription_job", {"TranscriptionJob": trabajo("QUEUED")}, _parametros_inicio())
    r = _post(cliente)
    assert r.status_code == 202
    cuerpo = validar(r.json())
    assert cuerpo == ejemplo("transcribiendo")


def test_post_usa_el_idioma_pedido(aws, cliente):
    aws.trabajo_no_existe()
    aws.sube_audio()
    aws.transcribe.add_response(
        "start_transcription_job", {"TranscriptionJob": trabajo("QUEUED", LanguageCode="es-MX")}, _parametros_inicio("es-MX")
    )
    assert validar(_post(cliente, idioma="es-MX").json())["idioma"] == "es-MX"


def test_post_repetido_devuelve_el_resultado_final(aws, cliente):
    aws.trabajo_existe(trabajo("COMPLETED"))
    aws.objeto(f"resultados/{ID}.json", ejemplo("completado"))
    r = _post(cliente)
    assert r.status_code == 200
    assert validar(r.json()) == ejemplo("completado")


def test_post_repetido_en_curso_no_vuelve_a_subir_audio(aws, cliente):
    aws.trabajo_existe(trabajo("IN_PROGRESS"))
    aws.objeto_no_existe(f"resultados/{ID}.json")
    r = _post(cliente)
    assert r.status_code == 202
    assert validar(r.json())["estado"] == "transcribiendo"


def test_post_simultaneo_usa_el_trabajo_que_gano(aws, cliente):
    aws.trabajo_no_existe()
    aws.sube_audio()
    aws.transcribe.add_client_error("start_transcription_job", service_error_code="ConflictException", http_status_code=409)
    aws.trabajo_existe(trabajo("IN_PROGRESS"))
    aws.objeto_no_existe(f"resultados/{ID}.json")
    assert _post(cliente).status_code == 202


def test_post_id_usado_por_otro_servicio(aws, cliente):
    aws.trabajo_existe(trabajo("COMPLETED", bucket="otro-bucket"))
    r = _post(cliente)
    assert r.status_code == 409
    assert r.json()["error"]["codigo"] == "id_en_uso"


@pytest.mark.parametrize(
    ("codigo_aws", "estado_http", "codigo"),
    [
        ("ThrottlingException", 503, "servicio_saturado"),
        ("LimitExceededException", 503, "servicio_saturado"),
        ("AccessDeniedException", 502, "error_proveedor"),
    ],
)
def test_post_errores_de_aws(aws, cliente, codigo_aws, estado_http, codigo):
    aws.trabajo_no_existe()
    aws.sube_audio()
    aws.transcribe.add_client_error("start_transcription_job", service_error_code=codigo_aws, http_status_code=400)
    r = _post(cliente)
    assert r.status_code == estado_http
    assert r.json()["error"]["codigo"] == codigo
    if estado_http == 503:
        assert r.headers["retry-after"] == "5"


def test_post_tiempo_agotado(aws, cliente, monkeypatch):
    def lento(*_args):
        raise ReadTimeoutError(endpoint_url="https://transcribe.us-east-1.amazonaws.com")

    monkeypatch.setattr(aws.servicio, "iniciar", lento)
    r = _post(cliente)
    assert r.status_code == 504
    assert r.json()["error"]["codigo"] == "tiempo_agotado"


@pytest.mark.parametrize(
    ("cambios", "estado_http", "codigo"),
    [
        ({"audio_base64": "esto no es base64!"}, 400, "base64_invalido"),
        ({"audio_base64": ""}, 400, "audio_vacio"),
        ({"audio_base64": base64.b64encode(b"texto plano, no audio").decode()}, 415, "formato_no_soportado"),
        ({"id_captura": "CAP 12/../x"}, 422, "solicitud_invalida"),
        ({"idioma": "es-CL"}, 422, "solicitud_invalida"),
        ({"audio_base64": None}, 422, "solicitud_invalida"),
    ],
)
def test_post_valida_la_entrada(aws, cliente, cambios, estado_http, codigo):
    r = _post(cliente, **cambios)
    assert r.status_code == estado_http
    assert r.json()["error"]["codigo"] == codigo


def test_post_audio_demasiado_grande(aws, cliente, monkeypatch):
    monkeypatch.setattr(aws.servicio, "config", replace(aws.servicio.config, max_bytes_audio=10))
    r = _post(cliente)
    assert r.status_code == 413
    assert r.json()["error"]["codigo"] == "audio_demasiado_grande"


def test_get_devuelve_el_resultado_guardado(aws, cliente):
    aws.objeto(f"resultados/{ID}.json", ejemplo("completado"))
    r = cliente.get(f"/api/transcripciones/{ID}")
    assert r.status_code == 200
    assert validar(r.json()) == ejemplo("completado")


def test_get_en_curso(aws, cliente):
    aws.objeto_no_existe(f"resultados/{ID}.json")
    aws.trabajo_existe(trabajo("IN_PROGRESS"))
    assert validar(cliente.get(f"/api/transcripciones/{ID}").json()) == ejemplo("transcribiendo")


def test_get_guarda_el_resultado_si_se_perdio_el_evento(aws, cliente):
    aws.objeto_no_existe(f"resultados/{ID}.json")
    aws.trabajo_existe(trabajo("COMPLETED"))
    aws.objeto(f"transcripciones/{ID}.json", CRUDO)
    aws.guarda_resultado()
    aws.borra_audio()
    assert validar(cliente.get(f"/api/transcripciones/{ID}").json()) == ejemplo("completado")


def test_get_trabajo_fallido(aws, cliente):
    aws.objeto_no_existe(f"resultados/{ID}.json")
    aws.trabajo_existe(trabajo("FAILED", FailureReason="Motivo de prueba"))
    aws.guarda_resultado()
    aws.borra_audio()
    cuerpo = validar(cliente.get(f"/api/transcripciones/{ID}").json())
    assert cuerpo["estado"] == "fallido"
    assert cuerpo["error"] == {"codigo": "transcripcion_fallida", "mensaje": "Motivo de prueba"}


def test_get_transcripcion_ya_borrada(aws, cliente):
    aws.objeto_no_existe(f"resultados/{ID}.json")
    aws.trabajo_existe(trabajo("COMPLETED"))
    aws.objeto_no_existe(f"transcripciones/{ID}.json")
    aws.guarda_resultado()
    aws.borra_audio()
    cuerpo = validar(cliente.get(f"/api/transcripciones/{ID}").json())
    assert cuerpo["error"]["codigo"] == "resultado_no_disponible"


def test_get_inexistente(aws, cliente):
    aws.objeto_no_existe(f"resultados/{ID}.json")
    aws.trabajo_no_existe()
    r = cliente.get(f"/api/transcripciones/{ID}")
    assert r.status_code == 404
    assert r.json()["error"]["codigo"] == "trabajo_no_encontrado"


def test_get_trabajo_de_otro_servicio(aws, cliente):
    aws.objeto_no_existe(f"resultados/{ID}.json")
    aws.trabajo_existe(trabajo("COMPLETED", bucket="otro-bucket"))
    assert cliente.get(f"/api/transcripciones/{ID}").status_code == 404


def test_get_otro_prefijo_no_llama_a_aws(aws, cliente):
    assert cliente.get("/api/transcripciones/otro-trabajo").status_code == 404


def test_get_id_invalido(aws, cliente):
    r = cliente.get("/api/transcripciones/tr-a$b")
    assert r.status_code == 422
    assert r.json()["error"]["codigo"] == "solicitud_invalida"


def test_salud(aws, cliente):
    assert cliente.get("/api/salud").json() == {"estado": "ok", "modo": "aws"}