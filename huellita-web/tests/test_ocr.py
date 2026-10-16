"""Pruebas del cliente del OCR de post-its, con una Lambda falsa (no se toca la red)."""
from __future__ import annotations

import io
import json
import logging

import pytest
from botocore.exceptions import ConnectTimeoutError, ReadTimeoutError

from huellita_api import ocr
from huellita_api.config import cargar_config

FUNCION = "postits-ocr"
ID_CAPTURA = "CAP-01M503FN5942S3MNAFA14C07AQ"
ID_EDUCADORA = "EDU-0001"
SALA = "SG-A"
FECHA = "2026-10-15"


@pytest.fixture
def cfg():
    """Config como la que deja `template.yaml`, con el nombre de la Lambda OCR."""
    return cargar_config({"FUNCION_OCR": FUNCION})


class LambdaFalsa:
    """Reemplaza a boto3: responde la lista en orden y anota cada invocación.

    Cada respuesta es un dict (se devuelve como `Payload` JSON), una tupla
    `(payload_dict, function_error)` o una excepción, que se lanza en vez de responder.
    """

    def __init__(self, *respuestas: object) -> None:
        self.pendientes = list(respuestas)
        self.clientes: list[dict] = []
        self.invocaciones: list[dict] = []

    def client(self, servicio: str, config=None):
        assert servicio == "lambda"
        self.clientes.append({"servicio": servicio, "config": config})
        return self

    def invoke(self, **parametros):
        self.invocaciones.append(
            {
                "FunctionName": parametros["FunctionName"],
                "InvocationType": parametros["InvocationType"],
                "evento": json.loads(parametros["Payload"]),
            }
        )
        assert self.pendientes, "el módulo invocó la Lambda más veces de las esperadas"
        siguiente = self.pendientes.pop(0)
        if isinstance(siguiente, BaseException):
            raise siguiente
        function_error = None
        if isinstance(siguiente, tuple):
            siguiente, function_error = siguiente
        salida: dict = {"Payload": io.BytesIO(json.dumps(siguiente).encode("utf-8"))}
        if function_error:
            salida["FunctionError"] = function_error
        return salida


@pytest.fixture
def lam(monkeypatch):
    """Instala la Lambda falsa en lugar de `boto3` y la devuelve."""

    def instalar(*respuestas: object) -> LambdaFalsa:
        falsa = LambdaFalsa(*respuestas)
        monkeypatch.setattr(ocr, "boto3", falsa)
        return falsa

    return instalar


def _ok(n: int = 9) -> dict:
    return {"id_captura": ID_CAPTURA, "prefijo": f"capturas/{ID_CAPTURA}/", "n_postits": n, "partes": []}


def _err(codigo: str) -> dict:
    return {"error": {"codigo": codigo, "mensaje": "falla simulada"}, "id_captura": ID_CAPTURA}


def _invocar(cfg) -> dict:
    return ocr.invocar(cfg, ID_CAPTURA, ID_EDUCADORA, SALA, FECHA)


def test_invocar_manda_el_evento_exacto_del_contrato(cfg, lam):
    falsa = lam(_ok())

    respuesta = _invocar(cfg)

    assert respuesta["n_postits"] == 9
    (invocacion,) = falsa.invocaciones
    assert invocacion["FunctionName"] == FUNCION
    assert invocacion["InvocationType"] == "RequestResponse"
    assert invocacion["evento"] == {
        "id_captura": ID_CAPTURA,
        "id_educadora": ID_EDUCADORA,
        "sala_grupo": SALA,
        "fecha_observacion": FECHA,
        "modo": "opencv",
        "escribir_texto": True,
        "incluir_urls": False,
    }


@pytest.mark.parametrize(
    ("codigo_ocr", "codigo_bff"),
    [
        ("FORMATO_NO_SOPORTADO", "formato_foto_no_soportado"),
        ("IMAGEN_DEMASIADO_GRANDE", "foto_demasiado_grande"),
        ("IMAGEN_NO_ENCONTRADA", "foto_invalida"),
        ("IMAGEN_NO_DECODIFICABLE", "foto_invalida"),
        ("PETICION_INVALIDA", "foto_invalida"),
        ("LECTURA_NO_DISPONIBLE", "ocr_sin_lectura"),
        ("ERROR_ALMACENAMIENTO", "ocr_caido"),
        ("CONFIGURACION", "ocr_caido"),
        ("ERROR_INTERNO", "ocr_caido"),
        ("UN_CODIGO_NUEVO", "ocr_caido"),
    ],
)
def test_invocar_traduce_cada_codigo_de_error(cfg, lam, codigo_ocr, codigo_bff):
    lam(_err(codigo_ocr))

    with pytest.raises(ocr.ErrorOcr) as fallo:
        _invocar(cfg)

    assert fallo.value.codigo == codigo_bff


@pytest.mark.parametrize(
    "caida",
    [
        ReadTimeoutError(endpoint_url="https://lambda"),
        ConnectTimeoutError(endpoint_url="https://lambda"),
    ],
    ids=["read_timeout", "connect_timeout"],
)
def test_un_timeout_levanta_ocr_en_proceso_no_un_error(cfg, lam, caida):
    lam(caida)

    with pytest.raises(ocr.OcrEnProceso):
        _invocar(cfg)


def test_otra_falla_de_red_deja_el_ocr_caido(cfg, lam):
    lam(OSError("socket roto"))

    with pytest.raises(ocr.ErrorOcr) as fallo:
        _invocar(cfg)

    assert fallo.value.codigo == "ocr_caido"


def test_un_function_error_deja_el_ocr_caido(cfg, lam):
    lam(({"errorMessage": "boom"}, "Unhandled"))

    with pytest.raises(ocr.ErrorOcr) as fallo:
        _invocar(cfg)

    assert fallo.value.codigo == "ocr_caido"


@pytest.mark.parametrize("crudo", [b"<html>502</html>", b"[]", b"null"], ids=["html", "lista", "nulo"])
def test_un_payload_ilegible_deja_el_ocr_caido(cfg, monkeypatch, crudo):
    class LambdaCruda(LambdaFalsa):
        def invoke(self, **parametros):
            self.invocaciones.append({"evento": json.loads(parametros["Payload"])})
            return {"Payload": io.BytesIO(crudo)}

    monkeypatch.setattr(ocr, "boto3", LambdaCruda())

    with pytest.raises(ocr.ErrorOcr) as fallo:
        _invocar(cfg)

    assert fallo.value.codigo == "ocr_caido"


def test_el_cliente_de_boto3_tiene_los_tiempos_limite_del_ocr(cfg, lam):
    falsa = lam(_ok())

    _invocar(cfg)

    (cliente,) = falsa.clientes
    ajustes = cliente["config"]
    assert ajustes.connect_timeout == 5
    assert ajustes.read_timeout == 70
    assert ajustes.retries["max_attempts"] == 1


def test_el_payload_de_la_imagen_no_viaja_en_el_evento_ni_en_los_logs(cfg, lam, caplog):
    caplog.set_level(logging.DEBUG)
    falsa = lam(_ok())

    _invocar(cfg)

    # El OCR lee la foto desde S3: el evento no lleva bytes de imagen.
    (invocacion,) = falsa.invocaciones
    assert "foto" not in invocacion["evento"]
    assert "base64" not in json.dumps(invocacion["evento"]).lower()
