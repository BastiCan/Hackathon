"""Tarea 3.4: postproceso.py consolida corridas (nivel, certeza, comentario)."""

from __future__ import annotations

from core.modelos import Certeza
from core.postproceso import (
    Corrida,
    CorridaCodigo,
    componer_comentario,
    consolidar,
)


def _corrida(codigos: list[str], otro: str | None = None, comentario: str = "") -> Corrida:
    return Corrida(
        codigos=[CorridaCodigo(id_manifestacion=c, frase_evidencia="evidencia") for c in codigos],
        otro_codigo_viable=otro,
        comentario=comentario,
    )


# --- certeza ---

def test_certeza_alta_todas_coinciden_sin_otro_viable() -> None:
    corridas = [_corrida(["MAN-L09-SE-02"], comentario="colabora espontaneamente") for _ in range(3)]
    c = consolidar(corridas)
    assert len(c.codigos) == 1
    assert c.codigos[0].id_manifestacion == "MAN-L09-SE-02"
    assert c.codigos[0].certeza == Certeza.ALTA


def test_certeza_media_si_alguna_marca_otro_viable() -> None:
    corridas = [
        _corrida(["MAN-L09-SE-02"]),
        _corrida(["MAN-L09-SE-02"]),
        _corrida(["MAN-L09-SE-02"], otro="MAN-L06-MG-02"),
    ]
    c = consolidar(corridas)
    assert c.codigos[0].certeza == Certeza.MEDIA


def test_certeza_media_si_mayoria_pero_no_todas() -> None:
    corridas = [
        _corrida(["MAN-L08-LC-01"]),
        _corrida(["MAN-L08-LC-01"]),
        _corrida(["MAN-L09-LC-01"]),
    ]
    c = consolidar(corridas)
    assert len(c.codigos) == 1
    assert c.codigos[0].id_manifestacion == "MAN-L08-LC-01"
    assert c.codigos[0].certeza == Certeza.MEDIA
    assert c.alternativas == ["MAN-L09-LC-01"]


def test_certeza_baja_sin_mayoria() -> None:
    # 3 corridas, 3 codigos distintos: ninguno tiene mayoria -> el mas votado, baja.
    corridas = [
        _corrida(["MAN-L07-MG-02"]),
        _corrida(["MAN-L08-MG-02"]),
        _corrida(["MAN-L09-MG-02"]),
    ]
    c = consolidar(corridas)
    assert all(cod.certeza == Certeza.BAJA for cod in c.codigos)


# --- varios dominios en una observacion ---

def test_dos_codigos_ambos_con_mayoria() -> None:
    corridas = [
        _corrida(["MAN-L09-SE-02", "MAN-L06-MG-02"]),
        _corrida(["MAN-L09-SE-02", "MAN-L06-MG-02"]),
        _corrida(["MAN-L09-SE-02"]),
    ]
    c = consolidar(corridas)
    ids = {cod.id_manifestacion for cod in c.codigos}
    assert ids == {"MAN-L09-SE-02", "MAN-L06-MG-02"}


# --- un codigo cuenta un voto por corrida aunque se repita ---

def test_codigo_repetido_en_una_corrida_cuenta_un_voto() -> None:
    corridas = [
        _corrida(["MAN-L09-SE-02", "MAN-L09-SE-02"]),
        _corrida(["MAN-L04-CO-01"]),
        _corrida(["MAN-L04-CO-01"]),
    ]
    c = consolidar(corridas)
    # MAN-L04-CO-01 tiene 2 votos (mayoria); MAN-L09-SE-02 solo 1.
    assert c.codigos[0].id_manifestacion == "MAN-L04-CO-01"
    assert "MAN-L09-SE-02" in c.alternativas


# --- sin correspondencia ---

def test_sin_correspondencia_cuando_no_hay_codigos() -> None:
    corridas = [_corrida([], comentario="ninguna candidata corresponde") for _ in range(3)]
    c = consolidar(corridas)
    assert c.sin_correspondencia
    assert c.comentario == "ninguna candidata corresponde"


def test_sin_corridas_devuelve_vacio() -> None:
    c = consolidar([])
    assert c.sin_correspondencia


# --- comentario ---

def test_comentario_base_viene_de_corrida_ganadora() -> None:
    corridas = [
        _corrida(["MAN-L08-LC-01"], comentario="combina dos palabras"),
        _corrida(["MAN-L08-LC-01"], comentario="combina dos palabras"),
        _corrida(["MAN-L09-LC-01"], comentario="tres palabras"),
    ]
    c = consolidar(corridas)
    assert c.comentario == "combina dos palabras"


def test_componer_comentario_agrega_alternativas_y_edad() -> None:
    texto = componer_comentario(
        base="Combina dos palabras: nivel 8.",
        alternativas=["MAN-L09-LC-01"],
        nota_edad="Para su edad (31 meses) lo esperado es el nivel 9.",
    )
    assert "Combina dos palabras: nivel 8." in texto
    assert "Otra lectura: MAN-L09-LC-01." in texto
    assert "Para su edad (31 meses)" in texto


def test_componer_comentario_sin_alternativas_ni_edad() -> None:
    assert componer_comentario("Solo base.", [], "") == "Solo base."
