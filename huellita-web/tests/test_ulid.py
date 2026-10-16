"""Pruebas del id de captura `CAP-<ULID>` (CONTRATOS.md §6)."""
from __future__ import annotations

import pytest

from huellita_api import ulid

EJEMPLO = "CAP-01M503FN5942S3MNAFA14C07AQ"  # id real de la cuenta del hackathon


def valor_de(texto: str) -> int:
    """Devuelve los bits que representa un ULID en base32 de Crockford."""
    valor = 0
    for caracter in texto:
        valor = valor * 32 + ulid.ALFABETO.index(caracter)
    return valor


def test_el_alfabeto_es_el_de_crockford() -> None:
    assert ulid.ALFABETO == "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    assert len(ulid.ALFABETO) == 32
    assert not set("ILOU") & set(ulid.ALFABETO)


def test_el_id_nuevo_calza_con_el_formato_obligatorio() -> None:
    id_captura = ulid.nuevo_id_captura()

    assert ulid.RE_ID_CAPTURA.match(id_captura)
    assert ulid.es_id_captura(id_captura)
    assert id_captura.startswith("CAP-")
    assert len(id_captura) == len("CAP-") + 26


def test_el_ejemplo_del_contrato_calza() -> None:
    assert ulid.es_id_captura(EJEMPLO)


def test_todos_los_caracteres_del_alfabeto_calzan_con_el_formato() -> None:
    # 26 caracteres armados con el alfabeto completo, para que la clase del
    # regex (0-9 A-H J K M N P-T V-Z) cubra exactamente el alfabeto.
    for caracter in ulid.ALFABETO:
        assert ulid.es_id_captura("CAP-" + caracter * 26)


@pytest.mark.parametrize(
    "valor",
    [
        "",
        "CAP-",
        EJEMPLO.lower(),
        EJEMPLO[:-1],  # 25 caracteres
        EJEMPLO + "A",  # 27 caracteres
        EJEMPLO.replace("CAP-", ""),
        "cap-" + EJEMPLO[4:],
        "CAP-01M503FN5942S3MNAFA14C07AI",  # la I no está en Crockford
        "CAP-01M503FN5942S3MNAFA14C07AL",  # la L tampoco
        "CAP-01M503FN5942S3MNAFA14C07AO",  # la O tampoco
        "CAP-01M503FN5942S3MNAFA14C07AU",  # la U tampoco
        " " + EJEMPLO,
        EJEMPLO + " ",
    ],
)
def test_lo_que_no_calza_se_rechaza(valor: str) -> None:
    assert not ulid.es_id_captura(valor)


def test_los_48_bits_altos_son_el_tiempo_en_milisegundos() -> None:
    ms = 1_792_000_000_000

    valor = valor_de(ulid.nuevo_ulid(ms))

    assert valor >> ulid.BITS_AZAR == ms
    assert valor.bit_length() <= ulid.BITS_TIEMPO + ulid.BITS_AZAR


def test_el_tiempo_se_recorta_a_48_bits() -> None:
    valor = valor_de(ulid.nuevo_ulid((1 << ulid.BITS_TIEMPO) + 7))

    assert valor >> ulid.BITS_AZAR == 7


def test_el_tiempo_queda_en_los_primeros_10_caracteres() -> None:
    ms = 1_792_000_000_000

    primero = ulid.nuevo_ulid(ms)
    segundo = ulid.nuevo_ulid(ms)

    assert primero[:10] == segundo[:10]
    assert primero[10:] != segundo[10:]  # los 80 bits de azar


def test_valores_conocidos_de_los_dos_extremos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ulid.secrets, "token_bytes", lambda cantidad: b"\x00" * cantidad)
    assert ulid.nuevo_ulid(0) == "0" * 26

    monkeypatch.setattr(ulid.secrets, "token_bytes", lambda cantidad: b"\xff" * cantidad)
    # 128 bits en 1: el primer carácter solo lleva los 3 bits que sobran.
    assert ulid.nuevo_ulid((1 << ulid.BITS_TIEMPO) - 1) == "7" + "Z" * 25


def test_el_azar_sale_de_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    pedidos: list[int] = []
    monkeypatch.setattr(ulid.secrets, "token_bytes", lambda cantidad: pedidos.append(cantidad) or b"\x00" * cantidad)

    ulid.nuevo_id_captura()

    assert pedidos == [10]  # 80 bits


def test_los_ids_no_se_repiten() -> None:
    ids = {ulid.nuevo_id_captura() for _ in range(500)}

    assert len(ids) == 500
