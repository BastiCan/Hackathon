"""Validación del audio y conversión de la salida de Transcribe."""
from __future__ import annotations

import base64

import pytest

from transcriptor.audio import AudioInvalido, decodificar_base64, detectar_formato
from transcriptor.conversion import convertir_salida

from conftest import CRUDO


@pytest.mark.parametrize(
    ("cabecera", "extension"),
    [
        (b"\x1a\x45\xdf\xa3\x9f\x42\x86\x81", "webm"),
        (b"OggS\x00\x02", "ogg"),
        (b"\x00\x00\x00\x20ftypM4A ", "m4a"),
        (b"\x00\x00\x00\x1cftypisom", "mp4"),
        (b"RIFF\x24\x08\x00\x00WAVEfmt ", "wav"),
        (b"fLaC\x00\x00\x00\x22", "flac"),
        (b"#!AMR\n", "amr"),
        (b"ID3\x04\x00", "mp3"),
        (b"\xff\xfb\x90\x64", "mp3"),
    ],
)
def test_detecta_formatos_aceptados(cabecera, extension):
    assert detectar_formato(cabecera + b"\x00" * 16).extension == extension


@pytest.mark.parametrize("datos", [b"\xff\xf1\x50\x80" + b"\x00" * 8, b"<html></html>", b"PK\x03\x04", b""])
def test_rechaza_otros_formatos(datos):
    assert detectar_formato(datos) is None


def test_acepta_data_url_y_saltos_de_linea():
    b64 = base64.b64encode(b"hola audio").decode()
    assert decodificar_base64(f"data:audio/webm;codecs=opus;base64,{b64[:4]}\n{b64[4:]}", 100) == b"hola audio"


def test_limite_de_tamano_exacto():
    assert decodificar_base64(base64.b64encode(b"x" * 10).decode(), 10) == b"x" * 10
    with pytest.raises(AudioInvalido) as error:
        decodificar_base64(base64.b64encode(b"x" * 11).decode(), 10)
    assert error.value.estado_http == 413


def test_convierte_la_salida_de_transcribe():
    texto, palabras, promedio = convertir_salida(CRUDO, 0.60)
    items = [i for i in CRUDO["results"]["items"] if i["type"] == "pronunciation"]
    assert texto == "Armó una torre de seis bloques y después ayudó a ordenar."
    assert len(palabras) == len(items) == 11
    assert [p.texto for p in palabras if p.dudosa] == ["torre"]
    assert (palabras[0].inicio_segundos, palabras[0].fin_segundos) == (0.42, 0.81)
    esperado = sum(float(i["alternatives"][0]["confidence"]) for i in items) / len(items)
    assert promedio == round(esperado, 4)


def _salida(*items: dict, texto: str = "hola") -> dict:
    return {"results": {"transcripts": [{"transcript": texto}], "items": list(items)}}


def _palabra(contenido: str, confianza: str) -> dict:
    return {"type": "pronunciation", "start_time": "0.0", "end_time": "0.5", "alternatives": [{"content": contenido, "confidence": confianza}]}


def test_umbral_de_palabra_dudosa_es_estricto():
    _, palabras, _ = convertir_salida(_salida(_palabra("a", "0.60"), _palabra("b", "0.5999")), 0.60)
    assert [p.dudosa for p in palabras] == [False, True]


def test_normaliza_tildes_a_nfc():
    texto, palabras, _ = convertir_salida(_salida(_palabra("Armo\u0301", "0.9"), texto="Armo\u0301"), 0.60)
    assert texto == palabras[0].texto == "Arm\u00f3"


def test_audio_sin_voz():
    assert convertir_salida({"results": {"transcripts": [{"transcript": ""}], "items": []}}, 0.60) == ("", [], None)


def test_salida_con_formato_inesperado():
    with pytest.raises(ValueError):
        convertir_salida({"resultados": {}}, 0.60)