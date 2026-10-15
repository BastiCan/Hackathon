"""Errores de la API: un código estable por caso y un mensaje en las palabras de la tía.

Los mensajes nunca nombran AWS, ni traen trazas, ni la clave del transcriptor: son lo único
que ve la tía cuando algo falla.
"""
from __future__ import annotations


class ErrorApi(Exception):
    """Falla esperada del BFF. `app.py` la traduce a `{"error": {"codigo", "mensaje"}}`."""

    def __init__(self, codigo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


CODIGOS_HTTP: dict[str, int] = {
    "sin_acceso": 403,
    "autora_desconocida": 422,
    "sala_desconocida": 404,
    "no_encontrado": 404,
    "solicitud_invalida": 422,
    "formato_no_soportado": 422,
    "texto_invalido": 422,
    "base64_invalido": 422,
    "sugerencia_desconocida": 404,
    "nino_de_otra_sala": 422,
    "audio_demasiado_grande": 413,
    "formato_audio_no_soportado": 415,
    "tope_diario": 429,
    "servicio_saturado": 503,
    "error_envio": 502,
    "transcriptor_caido": 502,
    "error_interno": 500,
}

MENSAJES: dict[str, str] = {
    "sin_acceso": "Esta sala no es tuya. Elige la tuya y vuelve a intentar.",
    "autora_desconocida": "No encontramos a esta tía. Vuelve a entrar con tu nombre.",
    "sala_desconocida": "Esta sala no está disponible en la demo.",
    "no_encontrado": "No encontramos lo que buscas.",
    "solicitud_invalida": "Falta algo en la nota. Revísala y vuelve a intentar.",
    "formato_no_soportado": "Por ahora solo podemos guardar notas escritas o grabadas.",
    "texto_invalido": "Escribe la nota: puede tener hasta 5000 caracteres.",
    "base64_invalido": "No pudimos leer la grabación. Vuelve a grabarla.",
    "sugerencia_desconocida": "Esta sugerencia ya no está. Vuelve a cargar la pantalla.",
    "nino_de_otra_sala": "Este niño o niña no es de esta sala.",
    "audio_demasiado_grande": "La grabación quedó muy larga. Graba una más corta.",
    "formato_audio_no_soportado": "No podemos leer este tipo de grabación. Vuelve a grabarla.",
    "tope_diario": "Llegaste al máximo de notas de hoy en esta sala. Sigue mañana.",
    "servicio_saturado": "Hay muchas notas en cola. Espera un momento e intenta de nuevo.",
    "error_envio": "No pudimos guardar esta nota. Intenta de nuevo.",
    "transcriptor_caido": "No pudimos leer la grabación ahora. Intenta de nuevo en unos minutos.",
    "error_interno": "Algo falló de nuestro lado. Intenta de nuevo.",
}

MENSAJE_POR_DEFECTO = "Algo falló de nuestro lado. Intenta de nuevo."


def error(codigo: str) -> ErrorApi:
    """Arma el `ErrorApi` de un código con su mensaje para la tía."""
    return ErrorApi(codigo, MENSAJES.get(codigo, MENSAJE_POR_DEFECTO))


def estado_http(codigo: str) -> int:
    """Estado HTTP de un código; 500 si el código no está en la tabla."""
    return CODIGOS_HTTP.get(codigo, 500)
