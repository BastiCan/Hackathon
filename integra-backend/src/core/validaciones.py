"""Validaciones en codigo de la salida del LLM (sin IA).

- `texto_literal` de cada fragmento debe existir en la nota original.
- Si queda texto sustantivo sin asignar -> advertencia TEXTO_NO_CUBIERTO (a nivel captura).
- `frase_evidencia` de cada codigo debe ser literal del fragmento.
Comparacion normalizada (dominio.md Seccion 3): minusculas, sin tildes, espacios colapsados.
"""

from __future__ import annotations

import re
import unicodedata

ADVERTENCIA_TEXTO_NO_CUBIERTO = "TEXTO_NO_CUBIERTO"

# Minimo de caracteres (ya normalizados) para considerar "sustantivo" un sobrante.
_MIN_SUSTANTIVO = 10


def normalizar_texto(texto: str) -> str:
    """Minusculas, sin tildes, sin puntuacion, espacios colapsados (comparar literalidad).

    Las notas son informales (puntos, comas, guiones de lista): la puntuacion no debe
    romper la comparacion. Se conservan letras y numeros; el resto pasa a ser separador.
    """
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    sin_puntuacion = re.sub(r"[^0-9a-zA-Z\u00f1\u00d1 ]+", " ", sin_tildes.lower())
    return " ".join(sin_puntuacion.split())


def es_literal(fragmento: str, original: str) -> bool:
    """True si `fragmento` aparece en `original` (comparacion normalizada)."""
    f = normalizar_texto(fragmento)
    if f == "":
        return False
    return f in normalizar_texto(original)


def frase_evidencia_valida(frase: str, fragmento: str) -> bool:
    """La frase de evidencia debe ser literal del fragmento (comparacion normalizada)."""
    return es_literal(frase, fragmento)


def refs_validas(refs: list[str | None], refs_nomina: set[str]) -> bool:
    """Toda ref no nula debe existir en la nomina (una ref inventada es invalida)."""
    return all(ref in refs_nomina for ref in refs if ref is not None)


def _tokens_cubiertos(fragmentos: list[str]) -> set[str]:
    tokens: set[str] = set()
    for frag in fragmentos:
        tokens.update(normalizar_texto(frag).split())
    return tokens


def texto_no_cubierto(original: str, fragmentos: list[str]) -> bool:
    """True si queda texto sustantivo del original sin aparecer en ningun fragmento.

    Heuristica: se juntan las palabras de todos los fragmentos y se busca una corrida
    de palabras del original ausentes de esa union. Si esa corrida (unida) supera
    `_MIN_SUSTANTIVO` caracteres normalizados, se considera no cubierto.
    """
    cubiertos = _tokens_cubiertos(fragmentos)
    palabras = normalizar_texto(original).split()

    corrida: list[str] = []
    for palabra in palabras:
        if palabra in cubiertos:
            corrida = []
            continue
        corrida.append(palabra)
        if len(" ".join(corrida)) >= _MIN_SUSTANTIVO:
            return True
    return False


def normalizar_apostrofos(texto: str) -> str:
    """Unifica comillas tipograficas a comillas rectas (ayuda a comparar literalidad)."""
    return re.sub(r"[\u2018\u2019\u201c\u201d]", "'", texto)
