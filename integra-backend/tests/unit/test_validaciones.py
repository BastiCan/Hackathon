"""Tarea 3.3: validaciones.py (literalidad, cobertura, refs, frase de evidencia)."""

from __future__ import annotations

from core.validaciones import (
    es_literal,
    frase_evidencia_valida,
    normalizar_texto,
    refs_validas,
    texto_no_cubierto,
)

# --- normalizar_texto / es_literal ---

def test_es_literal_ignora_tildes_mayusculas_y_espacios() -> None:
    original = "Sofía mira por la ventana y dice 'viene el Alexi'"
    assert es_literal("SOFIA   mira por la ventana", original)


def test_es_literal_falla_si_no_aparece() -> None:
    assert not es_literal("corrió hasta la reja", "Sofia mira por la ventana")


def test_es_literal_vacio_es_falso() -> None:
    assert not es_literal("   ", "cualquier cosa")


def test_normalizar_colapsa_espacios() -> None:
    assert normalizar_texto("  dos   palabras ") == "dos palabras"


# --- frase_evidencia_valida ---

def test_frase_evidencia_literal_del_fragmento() -> None:
    frag = "clasificaron hojas por tamaño"
    assert frase_evidencia_valida("hojas por tamaño", frag)


def test_frase_evidencia_inventada_invalida() -> None:
    frag = "clasificaron hojas por tamaño"
    assert not frase_evidencia_valida("ordenó bloques", frag)


# --- refs_validas ---

def test_refs_validas_todas_en_nomina() -> None:
    assert refs_validas(["N1", "N3", None], {"N1", "N2", "N3"})


def test_ref_inventada_invalida() -> None:
    assert not refs_validas(["N9"], {"N1", "N2"})


def test_refs_solo_nulas_son_validas() -> None:
    assert refs_validas([None, None], {"N1"})


# --- texto_no_cubierto ---

def test_texto_totalmente_cubierto() -> None:
    original = "Pedro clasifico hojas. Hoy bajo la asistencia."
    fragmentos = ["Pedro clasifico hojas", "Hoy bajo la asistencia"]
    assert not texto_no_cubierto(original, fragmentos)


def test_texto_con_sobrante_sustantivo() -> None:
    original = "Pedro clasifico hojas y despues jugo mucho rato en el patio con la pelota"
    fragmentos = ["Pedro clasifico hojas"]
    assert texto_no_cubierto(original, fragmentos)


def test_sobrante_minusculo_no_cuenta() -> None:
    # Solo queda "y" sin cubrir: no es sustantivo.
    original = "Pedro clasifico hojas y canto"
    fragmentos = ["Pedro clasifico hojas", "canto"]
    assert not texto_no_cubierto(original, fragmentos)
