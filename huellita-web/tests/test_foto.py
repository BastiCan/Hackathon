"""Pruebas de `datos/foto.py`: decodifica/valida la imagen e invoca el OCR.

Usa los dobles de `test_capturas` (Almacen en memoria, sin DynamoDB) y un OCR
falso: ni S3 ni la Lambda se tocan de verdad.
"""
from __future__ import annotations

import base64
import importlib

import pytest

from huellita_api import errores, ocr
from huellita_api.config import Config
from test_capturas import Almacen, cfg_de_prueba, instalar_dobles_de_rutas

instalar_dobles_de_rutas()

foto = importlib.import_module("huellita_api.datos.foto")
capturas = importlib.import_module("huellita_api.datos.capturas")

ID_CAPTURA = "CAP-01M503FN5942S3MNAFA14C07AQ"
ID_EDUCADORA = "EDU-0001"
SALA = "SG-A"
FECHA = "2026-10-15"

JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 32
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
HEIC = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 16


def _b64(crudo: bytes) -> str:
    return base64.b64encode(crudo).decode("ascii")


def test_decodifica_un_jpeg_valido() -> None:
    datos, tipo = foto.decodificar(_b64(JPEG))
    assert datos == JPEG
    assert tipo == "image/jpeg"


def test_decodifica_un_png_valido() -> None:
    datos, tipo = foto.decodificar(_b64(PNG))
    assert datos == PNG
    assert tipo == "image/png"


@pytest.mark.parametrize("valor", [None, "", "no-es-base64!!", "###"])
def test_rechaza_base64_roto_o_vacio_con_foto_invalida(valor) -> None:
    with pytest.raises(errores.ErrorApi) as fallo:
        foto.decodificar(valor)
    assert fallo.value.codigo == "foto_invalida"


def test_rechaza_heic_con_formato_no_soportado() -> None:
    with pytest.raises(errores.ErrorApi) as fallo:
        foto.decodificar(_b64(HEIC))
    assert fallo.value.codigo == "formato_foto_no_soportado"


def test_rechaza_bytes_sin_formato_conocido_con_foto_invalida() -> None:
    with pytest.raises(errores.ErrorApi) as fallo:
        foto.decodificar(_b64(b"\x00" * 64))
    assert fallo.value.codigo == "foto_invalida"


def test_rechaza_una_foto_sobre_el_tope_con_foto_demasiado_grande() -> None:
    grande = JPEG + b"\x00" * (foto.MAX_BYTES_FOTO + 1)
    with pytest.raises(errores.ErrorApi) as fallo:
        foto.decodificar(_b64(grande))
    assert fallo.value.codigo == "foto_demasiado_grande"


@pytest.fixture
def entorno(monkeypatch: pytest.MonkeyPatch) -> tuple[Config, Almacen]:
    """Config de prueba y un Almacen con una fila ya creada en `enviando`."""
    cfg = cfg_de_prueba()
    almacen = Almacen()
    almacen.conectar(monkeypatch)
    almacen.filas(cfg.tabla_capturas)[ID_CAPTURA] = {
        "id_captura": {"S": ID_CAPTURA},
        "sala_key": {"S": cfg.sala_key(SALA)},
        "estado_envio": {"S": "enviando"},
    }
    return cfg, almacen


def _estado(almacen: Almacen, cfg: Config) -> str:
    return almacen.fila(cfg.tabla_capturas, ID_CAPTURA)["estado_envio"]["S"]


def test_enviar_invoca_el_ocr_y_deja_la_fila_enviada(
    monkeypatch: pytest.MonkeyPatch, entorno: tuple[Config, Almacen]
) -> None:
    cfg, almacen = entorno
    llamadas: list[tuple] = []

    def invocar(c, id_captura, id_educadora, sala_grupo, fecha):
        llamadas.append((id_captura, id_educadora, sala_grupo, fecha))
        return {"n_postits": 3}

    monkeypatch.setattr(ocr, "invocar", invocar)

    foto.enviar(cfg, ID_CAPTURA, ID_EDUCADORA, SALA, FECHA)

    assert llamadas == [(ID_CAPTURA, ID_EDUCADORA, SALA, FECHA)]
    assert _estado(almacen, cfg) == "enviada"


def test_enviar_marca_error_envio_ante_error_ocr_y_relanza(
    monkeypatch: pytest.MonkeyPatch, entorno: tuple[Config, Almacen]
) -> None:
    cfg, almacen = entorno

    def invocar(*_args):
        raise ocr.ErrorOcr("ocr_sin_lectura")

    monkeypatch.setattr(ocr, "invocar", invocar)

    with pytest.raises(errores.ErrorApi) as fallo:
        foto.enviar(cfg, ID_CAPTURA, ID_EDUCADORA, SALA, FECHA)

    assert fallo.value.codigo == "ocr_sin_lectura"
    assert _estado(almacen, cfg) == "error_envio"


def test_enviar_no_falla_ante_ocr_en_proceso_y_deja_la_fila_enviada(
    monkeypatch: pytest.MonkeyPatch, entorno: tuple[Config, Almacen]
) -> None:
    cfg, almacen = entorno

    def invocar(*_args):
        raise ocr.OcrEnProceso

    monkeypatch.setattr(ocr, "invocar", invocar)

    foto.enviar(cfg, ID_CAPTURA, ID_EDUCADORA, SALA, FECHA)

    assert _estado(almacen, cfg) == "enviada"
