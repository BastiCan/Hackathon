"""Modo mock y el handler de Lambda con un evento simulado de API Gateway REST."""
from __future__ import annotations

import base64
import json

import pytest

from transcriptor.app import handler

from conftest import WEBM, validar

B64 = base64.b64encode(WEBM).decode()


def test_mock_post_y_get(mock, cliente):
    r = cliente.post("/api/transcripciones/audio", json={"id_captura": "CAP-1", "audio_base64": B64})
    assert r.status_code == 202
    assert validar(r.json())["proveedor"] == "mock"
    cuerpo = validar(cliente.get("/api/transcripciones/tr-CAP-1").json())
    assert cuerpo["estado"] == "completado"
    assert [p["texto"] for p in cuerpo["palabras"] if p["dudosa"]] == ["torre"]


@pytest.mark.parametrize(("id_captura", "estado"), [("CAP-fallido", "fallido"), ("CAP-transcribiendo", "transcribiendo")])
def test_mock_simula_estados(mock, cliente, id_captura, estado):
    assert validar(cliente.get(f"/api/transcripciones/tr-{id_captura}").json())["estado"] == estado


def test_mock_valida_el_audio(mock, cliente):
    r = cliente.post("/api/transcripciones/audio", json={"id_captura": "CAP-1", "audio_base64": "bm8gZXMgYXVkaW8="})
    assert r.status_code == 415


def _evento_rest(metodo: str, ruta: str, cuerpo: dict | None = None) -> dict:
    cabeceras = {"Content-Type": "application/json", "Host": "abc123.execute-api.us-east-1.amazonaws.com", "x-api-key": "clave"}
    return {
        "resource": ruta,
        "path": ruta,
        "httpMethod": metodo,
        "headers": cabeceras,
        "multiValueHeaders": {k: [v] for k, v in cabeceras.items()},
        "queryStringParameters": None,
        "multiValueQueryStringParameters": None,
        "pathParameters": None,
        "stageVariables": None,
        "requestContext": {
            "resourcePath": ruta,
            "httpMethod": metodo,
            "path": f"/v1{ruta}",
            "stage": "v1",
            "requestId": "solicitud-prueba",
            "accountId": "111122223333",
            "apiId": "abc123",
            "protocol": "HTTP/1.1",
            "identity": {"sourceIp": "203.0.113.10", "apiKey": "clave"},
        },
        "body": None if cuerpo is None else json.dumps(cuerpo),
        "isBase64Encoded": False,
    }


def test_lambda_con_evento_de_api_gateway(mock):
    r = handler(_evento_rest("POST", "/api/transcripciones/audio", {"id_captura": "CAP-9", "audio_base64": B64}), None)
    assert r["statusCode"] == 202
    assert validar(json.loads(r["body"]))["id_trabajo"] == "tr-CAP-9"
    r = handler(_evento_rest("GET", "/api/transcripciones/tr-CAP-9"), None)
    assert r["statusCode"] == 200
    assert validar(json.loads(r["body"]))["estado"] == "completado"