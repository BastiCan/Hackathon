"""Pruebas de la aplicación: forma única de los errores, CORS, routers y handler de Lambda."""
from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from mangum import Mangum
from starlette.requests import Request

from huellita_api import app as modulo_app
from huellita_api import auth, errores
from huellita_api.rutas import lectura as rutas_lectura


def codigo_de(respuesta) -> str:
    """Comprueba la forma `{"error": {"codigo", "mensaje"}}` y devuelve el código."""
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"error"}
    assert set(cuerpo["error"]) == {"codigo", "mensaje"}
    assert cuerpo["error"]["mensaje"].strip()
    return cuerpo["error"]["codigo"]


def rutas_declaradas() -> set[str]:
    """Las rutas montadas en la app, tal como quedan en `app.routes`."""
    return {ruta.path for ruta in modulo_app.app.routes}


@pytest.fixture
def cliente() -> TestClient:
    return TestClient(modulo_app.app)


@pytest.fixture
def cliente_tolerante() -> TestClient:
    """No relanza las excepciones del servidor: así se puede mirar el cuerpo del 500."""
    return TestClient(modulo_app.app, raise_server_exceptions=False)


def test_salud_responde_ok_sin_tocar_aws(cliente: TestClient) -> None:
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok"}


def test_ruta_inexistente_responde_no_encontrado(cliente: TestClient) -> None:
    respuesta = cliente.get("/api/no-existe")
    assert respuesta.status_code == 404
    assert codigo_de(respuesta) == "no_encontrado"


def test_metodo_no_permitido_responde_no_encontrado(cliente: TestClient) -> None:
    respuesta = cliente.post("/api/salud")
    assert respuesta.status_code == 404
    assert codigo_de(respuesta) == "no_encontrado"


def test_error_api_viaja_con_su_codigo_y_su_estado(cliente: TestClient) -> None:
    respuesta = cliente.get("/api/salas/SG-A/ninos")
    assert respuesta.status_code == errores.estado_http("sin_acceso") == 403
    assert codigo_de(respuesta) == "sin_acceso"
    assert respuesta.json()["error"]["mensaje"] == errores.MENSAJES["sin_acceso"]


def test_cuerpo_invalido_responde_solicitud_invalida() -> None:
    solicitud = Request({"type": "http", "method": "POST", "path": "/api/capturas", "headers": []})
    respuesta = asyncio.run(modulo_app.manejar_validacion(solicitud, RequestValidationError([])))
    assert respuesta.status_code == 422
    cuerpo = json.loads(respuesta.body)
    assert cuerpo["error"]["codigo"] == "solicitud_invalida"
    assert cuerpo["error"]["mensaje"] == errores.MENSAJES["solicitud_invalida"]


def test_excepcion_inesperada_responde_error_interno_sin_detalles(
    cliente_tolerante: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class LectorQueFalla:
        def leer_contexto(self, cfg):
            raise RuntimeError("ResourceNotFoundException: Requested resource not found: Table: Jardines")

    monkeypatch.setattr(rutas_lectura, "dar_lectura", LectorQueFalla)
    respuesta = cliente_tolerante.get("/api/contexto")
    assert respuesta.status_code == 500
    assert codigo_de(respuesta) == "error_interno"
    assert "Table" not in respuesta.text
    assert "Traceback" not in respuesta.text


def test_cors_abre_el_origen_y_la_cabecera_de_usuaria(cliente: TestClient) -> None:
    respuesta = cliente.options(
        "/api/salud",
        headers={
            "Origin": "https://d111111abcdef8.cloudfront.net",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "content-type, x-usuaria-id",
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == "*"
    permitidas = respuesta.headers["access-control-allow-headers"].lower()
    assert "x-usuaria-id" in permitidas
    assert "content-type" in permitidas
    assert "PUT" in respuesta.headers["access-control-allow-methods"]


def test_cors_viaja_en_las_respuestas_simples(cliente: TestClient) -> None:
    respuesta = cliente.get("/api/salud", headers={"Origin": "https://d111111abcdef8.cloudfront.net"})
    assert respuesta.headers["access-control-allow-origin"] == "*"


def test_las_rutas_del_contrato_quedan_montadas_bajo_api() -> None:
    """Las ocho rutas del contrato (CONTRATOS.md §4), con `path` legible en `app.routes`."""
    assert {
        "/api/salud",
        "/api/contexto",
        "/api/salas/{sala_id}/ninos",
        "/api/ninos/{id_nino}",
        "/api/salas/{sala_id}/registros",
        "/api/capturas",
        "/api/capturas/{id_captura}/archivar",
        "/api/decisiones",
    } <= rutas_declaradas()


def test_los_tres_routers_se_montan_siempre() -> None:
    assert modulo_app.ROUTERS_INCLUIDOS == ["lectura", "capturas", "decisiones"]
    assert set(rutas_declaradas()) >= {"/api/salud", "/api/capturas", "/api/decisiones"}


def test_las_rutas_montadas_tambien_salen_en_el_esquema_publico() -> None:
    assert {"/api/salud", "/api/capturas", "/api/decisiones"} <= set(
        modulo_app.app.openapi()["paths"]
    )


def test_la_config_se_lee_una_sola_vez() -> None:
    assert modulo_app.CFG is rutas_lectura.dar_config()
    assert "SG-A" in modulo_app.CFG.salas


def test_el_router_que_expone_configurar_recibe_la_config_de_la_app() -> None:
    recibidas: list[object] = []
    con_hook = SimpleNamespace(configurar=recibidas.append)
    assert modulo_app.pasar_config(con_hook) is True
    assert recibidas == [modulo_app.CFG]
    assert modulo_app.pasar_config(SimpleNamespace()) is False


def test_handler_es_mangum_sin_ciclo_de_vida() -> None:
    assert isinstance(modulo_app.handler, Mangum)
    assert modulo_app.handler.lifespan == "off"


@pytest.fixture
def bucle_de_eventos() -> Iterator[None]:
    """Mangum 0.22 llama a `asyncio.get_event_loop()`: en el proceso de pytest hay que dejarle uno."""
    bucle = asyncio.new_event_loop()
    asyncio.set_event_loop(bucle)
    try:
        yield
    finally:
        asyncio.set_event_loop(None)
        bucle.close()


def test_handler_atiende_un_evento_de_la_http_api(bucle_de_eventos: None) -> None:
    evento = {
        "version": "2.0",
        "routeKey": "ANY /api/{proxy+}",
        "rawPath": "/api/salud",
        "rawQueryString": "",
        "headers": {"host": "ejemplo.execute-api.us-east-1.amazonaws.com"},
        "requestContext": {
            "accountId": "277702547089",
            "apiId": "ejemplo",
            "domainName": "ejemplo.execute-api.us-east-1.amazonaws.com",
            "http": {
                "method": "GET",
                "path": "/api/salud",
                "protocol": "HTTP/1.1",
                "sourceIp": "190.0.0.1",
                "userAgent": "pytest",
            },
            "requestId": "id-de-prueba",
            "stage": "$default",
        },
        "isBase64Encoded": False,
    }
    respuesta = modulo_app.handler(evento, None)
    assert respuesta["statusCode"] == 200
    assert json.loads(respuesta["body"]) == {"estado": "ok"}


def test_usuarias_demo_son_las_dos_tias() -> None:
    assert auth.CABECERA_USUARIA == "X-Usuaria-Id"
    tias = auth.usuarias()
    assert [tia.id for tia in tias] == ["EDU-0001", "EDU-0002"]
    assert [tia.salaIds for tia in tias] == [["SG-A"], ["SG-B"]]
    assert {tia.rol for tia in tias} == {"tia"}
    assert {tia.jardinId for tia in tias} == {"JAR-0001"}
    assert auth.existe("EDU-0001")
    assert not auth.existe("EDU-9999")


def test_exigir_sala_mira_primero_la_demo_y_despues_la_tia() -> None:
    usuaria = auth.usuarias()[0]
    with pytest.raises(errores.ErrorApi) as fuera_de_la_demo:
        auth.exigir_sala(modulo_app.CFG, usuaria, "SG-Z")
    assert fuera_de_la_demo.value.codigo == "sala_desconocida"
    with pytest.raises(errores.ErrorApi) as ajena:
        auth.exigir_sala(modulo_app.CFG, usuaria, "SG-B")
    assert ajena.value.codigo == "sin_acceso"
    assert auth.exigir_sala(modulo_app.CFG, usuaria, "SG-A") is None
