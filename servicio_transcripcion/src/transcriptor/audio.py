"""Validación del audio recibido: base64, tamaño y formato según sus primeros bytes."""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass


class AudioInvalido(Exception):
    def __init__(self, estado_http: int, codigo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.estado_http = estado_http
        self.codigo = codigo
        self.mensaje = mensaje


@dataclass(frozen=True)
class FormatoAudio:
    extension: str
    tipo_mime: str


def decodificar_base64(texto: str, max_bytes: int) -> bytes:
    """Decodifica base64 estándar. Acepta un prefijo data:...;base64, y saltos de línea."""
    if texto.startswith("data:"):
        texto = texto.partition(",")[2]
    limpio = "".join(texto.split())
    if not limpio:
        raise AudioInvalido(400, "audio_vacio", "audio_base64 está vacío")
    if len(limpio) * 3 // 4 - limpio[-2:].count("=") > max_bytes:
        raise AudioInvalido(
            413,
            "audio_demasiado_grande",
            f"El audio supera {max_bytes} bytes. Grabe con menos bitrate (32 a 64 kbps) o en tramos más cortos",
        )
    try:
        datos = base64.b64decode(limpio, validate=True)
    except (binascii.Error, ValueError):
        raise AudioInvalido(400, "base64_invalido", "audio_base64 no es base64 estándar válido") from None
    if not datos:
        raise AudioInvalido(400, "audio_vacio", "audio_base64 está vacío")
    return datos


def detectar_formato(datos: bytes) -> FormatoAudio | None:
    """Reconoce los contenedores que acepta Transcribe por lotes. Devuelve None si no es uno de ellos."""
    c = datos[:12]
    if c.startswith(b"\x1a\x45\xdf\xa3"):  # EBML: WebM de MediaRecorder (Chrome, Firefox, Android)
        return FormatoAudio("webm", "audio/webm")
    if c.startswith(b"OggS"):
        return FormatoAudio("ogg", "audio/ogg")
    if c[4:8] == b"ftyp":  # MP4/M4A: Safari e iOS graban audio/mp4
        return FormatoAudio("m4a" if c[8:11] == b"M4A" else "mp4", "audio/mp4")
    if c.startswith(b"RIFF") and c[8:12] == b"WAVE":
        return FormatoAudio("wav", "audio/wav")
    if c.startswith(b"fLaC"):
        return FormatoAudio("flac", "audio/flac")
    if c.startswith(b"#!AMR"):
        return FormatoAudio("amr", "audio/amr")
    if c.startswith(b"ID3"):
        return FormatoAudio("mp3", "audio/mpeg")
    if len(c) > 1 and c[0] == 0xFF and (c[1] & 0xE0) == 0xE0 and (c[1] & 0x06) == 0x02:
        return FormatoAudio("mp3", "audio/mpeg")  # trama MPEG capa III sin etiqueta ID3
    return None