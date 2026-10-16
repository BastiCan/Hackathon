"""Pruebas del cliente del transcriptor, con un transcriptor falso (no se toca la red)."""
from __future__ import annotations

import io
import json
import logging
import urllib.error
import urllib.request

import pytest

from huellita_api import transcriptor
from huellita_api.config import cargar_config

CLAVE = "clave-secreta-de-prueba-9f3a4c"
ID_CLAVE = "14b8weklf1"
URL = "https://transcriptor.ejemplo/v1"
ID_CAPTURA = "CAP-01M503FN5942S3MNAFA14C07AQ"
ID_TRABAJO = f"tr-{ID_CAPTURA}"
AUDIO = "QUJDRA=="


@pytest.fixture
def cfg():
    """Config como la que deja `template.yaml`, con la URL del transcriptor y el id de la clave."""
    return cargar_config({"URL_TRANSCRIPTOR": URL + "/", "ID_CLAVE_TRANSCRIPTOR": ID_CLAVE})


class ApiGatewayFalso:
    """Reemplaza a boto3: entrega la clave y anota cómo se la pidieron."""

    def __init__(self, valor: str = CLAVE, falla: bool = False) -> None:
        self.valor = valor
        self.falla = falla
        self.clientes: list[dict] = []
        self.llamadas: list[dict] = []

    def client(self, servicio: str, config=None):
        assert servicio == "apigateway"
        self.clientes.append({"servicio": servicio, "config": config})
        return self

    def get_api_key(self, **parametros):
        self.llamadas.append(parametros)
        if self.falla:
            raise RuntimeError(f"AccessDenied al leer la clave {parametros['apiKey']}")
        return {"id": parametros["apiKey"], "value": self.valor, "enabled": True}


class _RespuestaFalsa:
    """Lo mínimo que usa el módulo de una respuesta de `urlopen`."""

    def __init__(self, estado: int, crudo: bytes) -> None:
        self.status = estado
        self._crudo = crudo

    def read(self) -> bytes:
        return self._crudo

    def __enter__(self) -> _RespuestaFalsa:
        return self

    def __exit__(self, *_: object) -> bool:
        return False


class TranscriptorFalso:
    """Transcriptor de mentira: anota cada solicitud y responde la lista en orden.

    Cada respuesta es `(estado, cuerpo)` —con el cuerpo como diccionario o como bytes— o una
    excepción, que se lanza en vez de responder.
    """

    def __init__(self, *respuestas: object) -> None:
        self.pendientes = list(respuestas)
        self.solicitudes: list[dict] = []

    def __call__(self, solicitud: urllib.request.Request, timeout: float | None = None):
        self.solicitudes.append(
            {
                "metodo": solicitud.get_method(),
                "url": solicitud.full_url,
                "cabeceras": {nombre.lower(): valor for nombre, valor in solicitud.header_items()},
                "cuerpo": json.loads(solicitud.data) if solicitud.data else None,
                "timeout": timeout,
            }
        )
        assert self.pendientes, "el módulo llamó al transcriptor más veces de las esperadas"
        siguiente = self.pendientes.pop(0)
        if isinstance(siguiente, BaseException):
            raise siguiente
        estado, cuerpo = siguiente
        crudo = cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        return _RespuestaFalsa(estado, crudo)


@pytest.fixture(autouse=True)
def api_gateway(monkeypatch):
    """Finge API Gateway y deja la clave sin cachear antes y después de cada prueba."""
    falso = ApiGatewayFalso()
    monkeypatch.setattr(transcriptor, "boto3", falso)
    transcriptor.valor_clave_api.cache_clear()
    yield falso
    transcriptor.valor_clave_api.cache_clear()


@pytest.fixture
def red(monkeypatch):
    """Instala el transcriptor falso en lugar de `urlopen` y lo devuelve."""

    def instalar(*respuestas: object) -> TranscriptorFalso:
        falso = TranscriptorFalso(*respuestas)
        monkeypatch.setattr(transcriptor.urllib.request, "urlopen", falso)
        return falso

    return instalar


def _http(estado: int, codigo: str = "error_proveedor") -> urllib.error.HTTPError:
    """Un error del transcriptor, con el cuerpo que manda de verdad."""
    cuerpo = json.dumps({"error": {"codigo": codigo, "mensaje": "falla simulada"}}).encode("utf-8")
    return urllib.error.HTTPError(URL, estado, "falla simulada", {}, io.BytesIO(cuerpo))


def _aceptado(id_trabajo: str = ID_TRABAJO) -> tuple[int, dict]:
    return 202, {"id_captura": ID_CAPTURA, "id_trabajo": id_trabajo, "estado": "transcribiendo"}


def test_iniciar_manda_el_cuerpo_exacto_y_devuelve_el_id_trabajo(cfg, red):
    falso = red(_aceptado())

    assert transcriptor.iniciar(cfg, ID_CAPTURA, AUDIO) == ID_TRABAJO

    (solicitud,) = falso.solicitudes
    assert solicitud["metodo"] == "POST"
    assert solicitud["url"] == f"{URL}/api/transcripciones/audio"
    assert solicitud["cuerpo"] == {"id_captura": ID_CAPTURA, "audio_base64": AUDIO}
    assert solicitud["cabeceras"]["x-api-key"] == CLAVE
    assert solicitud["cabeceras"]["content-type"] == "application/json"
    assert solicitud["timeout"] == transcriptor.TIEMPO_POST == 10


def test_iniciar_sin_id_trabajo_lo_arma_con_el_id_captura(cfg, red):
    red((200, {"id_captura": ID_CAPTURA, "estado": "completado"}))

    assert transcriptor.iniciar(cfg, ID_CAPTURA, AUDIO) == ID_TRABAJO


def test_iniciar_rechaza_un_estado_inesperado(cfg, red):
    red((204, b""))

    with pytest.raises(transcriptor.ErrorTranscriptor) as fallo:
        transcriptor.iniciar(cfg, ID_CAPTURA, AUDIO)

    assert fallo.value.codigo == "transcriptor_caido"
    assert fallo.value.estado == 204


@pytest.mark.parametrize(
    ("estado", "codigo"),
    [
        (413, "audio_demasiado_grande"),  # el BFF responde 413, igual
        (415, "formato_audio_no_soportado"),  # el BFF responde 415, igual
        (429, "servicio_saturado"),  # el BFF responde 503, "intenta de nuevo"
        (503, "servicio_saturado"),  # el BFF responde 503, "intenta de nuevo"
        (502, "transcriptor_caido"),  # el BFF responde 502
        (504, "transcriptor_caido"),  # el BFF responde 502
        (400, "transcriptor_caido"),
        (403, "transcriptor_caido"),
        (409, "transcriptor_caido"),
        (422, "transcriptor_caido"),
        (500, "transcriptor_caido"),
    ],
)
def test_iniciar_traduce_los_errores_del_transcriptor(cfg, red, estado, codigo):
    red(_http(estado))

    with pytest.raises(transcriptor.ErrorTranscriptor) as fallo:
        transcriptor.iniciar(cfg, ID_CAPTURA, AUDIO)

    assert fallo.value.codigo == codigo
    assert fallo.value.estado == estado


@pytest.mark.parametrize(
    "caida",
    [TimeoutError("se agotó el tiempo"), urllib.error.URLError("no hay red"), OSError("socket roto")],
    ids=["timeout", "sin_red", "socket"],
)
def test_una_caida_de_red_deja_el_transcriptor_caido(cfg, red, caida):
    red(caida)

    with pytest.raises(transcriptor.ErrorTranscriptor) as fallo:
        transcriptor.iniciar(cfg, ID_CAPTURA, AUDIO)

    assert fallo.value.codigo == "transcriptor_caido"
    assert fallo.value.estado is None


@pytest.mark.parametrize("crudo", [b"<html>502 Bad Gateway</html>", b"[]", b"null"], ids=["html", "lista", "nulo"])
def test_un_cuerpo_ilegible_deja_el_transcriptor_caido(cfg, red, crudo):
    red((202, crudo))

    with pytest.raises(transcriptor.ErrorTranscriptor) as fallo:
        transcriptor.iniciar(cfg, ID_CAPTURA, AUDIO)

    assert fallo.value.codigo == "transcriptor_caido"


def test_consultar_devuelve_el_json_y_espera_poco(cfg, red):
    cuerpo = {
        "id_captura": ID_CAPTURA,
        "id_trabajo": ID_TRABAJO,
        "estado": "completado",
        "texto_completo": "Nayara apiló cinco cubos y dijo torre",
        "confianza_agregada": 0.93,
    }
    falso = red((200, cuerpo))

    assert transcriptor.consultar(cfg, ID_TRABAJO) == cuerpo

    (solicitud,) = falso.solicitudes
    assert solicitud["metodo"] == "GET"
    assert solicitud["url"] == f"{URL}/api/transcripciones/{ID_TRABAJO}"
    assert solicitud["cuerpo"] is None
    assert solicitud["cabeceras"]["x-api-key"] == CLAVE
    assert solicitud["timeout"] == transcriptor.TIEMPO_GET == 3


@pytest.mark.parametrize(
    ("cuerpo", "estado", "texto"),
    [
        ({"estado": "transcribiendo", "texto_completo": None}, "transcribiendo", None),
        ({"estado": "completado", "texto_completo": "dijo torre"}, "completado", "dijo torre"),
        (
            {"estado": "fallido", "texto_completo": None, "error": {"codigo": "transcripcion_fallida", "mensaje": "x"}},
            "fallido",
            None,
        ),
    ],
    ids=["transcribiendo", "completado", "fallido"],
)
def test_consultar_entrega_los_tres_estados(cfg, red, cuerpo, estado, texto):
    red((200, cuerpo))

    respuesta = transcriptor.consultar(cfg, ID_TRABAJO)

    assert respuesta["estado"] == estado
    assert respuesta["texto_completo"] == texto


def test_consultar_un_trabajo_que_ya_no_esta_queda_fallido(cfg, red):
    red(_http(404, "trabajo_no_encontrado"))

    assert transcriptor.consultar(cfg, ID_TRABAJO) == {"estado": "fallido", "texto_completo": None}


@pytest.mark.parametrize(
    ("estado", "codigo"),
    [(429, "servicio_saturado"), (503, "servicio_saturado"), (502, "transcriptor_caido"), (504, "transcriptor_caido")],
)
def test_consultar_traduce_los_errores_del_transcriptor(cfg, red, estado, codigo):
    red(_http(estado))

    with pytest.raises(transcriptor.ErrorTranscriptor) as fallo:
        transcriptor.consultar(cfg, ID_TRABAJO)

    assert fallo.value.codigo == codigo
    assert fallo.value.estado == estado


def test_la_clave_se_pide_recien_al_primer_uso_y_una_sola_vez(cfg, red, api_gateway):
    red(_aceptado(), (200, {"estado": "transcribiendo", "texto_completo": None}))
    assert api_gateway.llamadas == []

    transcriptor.iniciar(cfg, ID_CAPTURA, AUDIO)
    transcriptor.consultar(cfg, ID_TRABAJO)

    assert api_gateway.llamadas == [{"apiKey": ID_CLAVE, "includeValue": True}]


def test_el_cliente_de_boto3_tiene_los_tiempos_limite_del_equipo(cfg, red, api_gateway):
    red(_aceptado())

    transcriptor.iniciar(cfg, ID_CAPTURA, AUDIO)

    (cliente,) = api_gateway.clientes
    ajustes = cliente["config"]
    assert ajustes.connect_timeout == 3
    assert ajustes.read_timeout == 8
    assert ajustes.retries["mode"] == "standard"


def test_sin_clave_no_se_llama_al_transcriptor(cfg, red, api_gateway, caplog):
    caplog.set_level(logging.DEBUG)
    api_gateway.falla = True
    falso = red(_aceptado())

    with pytest.raises(transcriptor.ErrorTranscriptor) as fallo:
        transcriptor.iniciar(cfg, ID_CAPTURA, AUDIO)

    assert fallo.value.codigo == "transcriptor_caido"
    assert fallo.value.estado is None
    assert falso.solicitudes == []
    assert "AccessDenied" not in caplog.text


def test_la_clave_nunca_aparece_en_los_logs_ni_en_los_errores(cfg, red, api_gateway, caplog):
    caplog.set_level(logging.DEBUG)
    falso = red(
        _aceptado(),
        (200, {"estado": "completado", "texto_completo": "Nayara apiló cinco cubos"}),
        _http(413, "audio_demasiado_grande"),
        TimeoutError("se agotó el tiempo"),
        (202, b"<html>502 Bad Gateway</html>"),
    )

    transcriptor.iniciar(cfg, ID_CAPTURA, AUDIO)
    transcriptor.consultar(cfg, ID_TRABAJO)
    for _ in range(3):
        with pytest.raises(transcriptor.ErrorTranscriptor) as fallo:
            transcriptor.iniciar(cfg, ID_CAPTURA, AUDIO)
        assert CLAVE not in str(fallo.value)
        assert CLAVE not in repr(fallo.value.args)

    assert falso.solicitudes[0]["cabeceras"]["x-api-key"] == CLAVE, "la clave sí viaja en la cabecera"
    assert caplog.records, "se esperaban logs que revisar"
    assert CLAVE not in caplog.text
    for registro in caplog.records:
        assert CLAVE not in registro.getMessage()
        assert CLAVE not in str(registro.args)


def test_valor_clave_api_no_deja_la_clave_en_el_mensaje_del_error(cfg, api_gateway):
    api_gateway.falla = True

    with pytest.raises(transcriptor.ErrorTranscriptor) as fallo:
        transcriptor.valor_clave_api(cfg)

    assert str(fallo.value) == "transcriptor_caido"


def test_una_clave_vacia_deja_el_transcriptor_caido(cfg, api_gateway):
    api_gateway.valor = ""

    with pytest.raises(transcriptor.ErrorTranscriptor) as fallo:
        transcriptor.valor_clave_api(cfg)

    assert fallo.value.codigo == "transcriptor_caido"
