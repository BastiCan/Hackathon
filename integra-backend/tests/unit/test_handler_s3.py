"""Tarea 8d: ruteo del handler (S3 vs directo) y estados de Registros, sin AWS ni LLM.

Se parchea `leer_json_s3`, `crear_datos`, `_recursos` y `procesar_nota` para no tocar
S3/DynamoDB/Bedrock. Solo se verifica la logica de orquestacion del handler.
"""

from __future__ import annotations

from typing import Any

import pytest

import handler as h
from core.modelos import Educadora, EstadoRegistro, Observacion, Resultado, TipoObservacion

ID_CAP = "CAP-01J8Z3M4N5P6Q7R8S9T0V1W2X3"
BUCKET = "integra-capturas-123"


class FakeDatos:
    """Datos en memoria: registra upserts y guarda observaciones sin AWS."""

    def __init__(self) -> None:
        self.registros: dict[str, dict] = {}
        self.guardadas: list[Observacion] = []

    def educadora(self, id_educadora: str) -> Educadora | None:
        if id_educadora == "EDU-0001":
            return Educadora(id_educadora="EDU-0001", id_jardin="JAR-0001")
        return None

    def ninos_de_jardin(self, id_jardin: str):
        return []

    def guardar_observaciones(self, observaciones, id_captura="", cabecera=None, **kw) -> None:
        self.guardadas.extend(observaciones)

    def upsert_registro(self, id_captura: str, campos: dict) -> None:
        self.registros.setdefault(id_captura, {}).update(campos)


def _s3_event(sufijo: str) -> dict:
    return {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": BUCKET},
                    "object": {"key": f"capturas/{ID_CAP}/{sufijo}"},
                },
            }
        ]
    }


@pytest.fixture
def fake(monkeypatch) -> FakeDatos:
    datos = FakeDatos()
    monkeypatch.setattr(h, "crear_datos", lambda: datos)
    monkeypatch.setattr(h, "_recursos", lambda: (object(), object(), {}))
    return datos


# --- meta.json ---

def test_meta_recibido(fake, monkeypatch) -> None:
    meta = {
        "id_educadora": "EDU-0001",
        "sala_grupo": "SG-A",
        "fecha_observacion": "2026-10-15",
        "tipo": "manual",
    }
    monkeypatch.setattr(h, "leer_json_s3", lambda b, k: meta)
    resp = h.handler(_s3_event("meta.json"))
    reg = fake.registros[ID_CAP]
    assert reg["estado"] == EstadoRegistro.RECIBIDO.value
    assert reg["sala_key"] == "JAR-0001#SG-A"
    assert reg["id_educadora"] == "EDU-0001"
    assert reg["fecha_observacion"] == "2026-10-15"
    assert resp["procesados"][0]["estado"] == EstadoRegistro.RECIBIDO.value


def test_meta_invalida(fake, monkeypatch) -> None:
    def _boom(b, k):
        raise ValueError("no existe")

    monkeypatch.setattr(h, "leer_json_s3", _boom)
    h.handler(_s3_event("meta.json"))
    assert fake.registros[ID_CAP]["estado"] == EstadoRegistro.ERROR.value
    assert fake.registros[ID_CAP]["error"] == "META_INVALIDA"


# --- texto.json ---

def test_texto_sin_texto(fake, monkeypatch) -> None:
    meta = {"id_educadora": "EDU-0001", "sala_grupo": "SG-A", "fecha_observacion": "2026-10-15"}

    def _leer(b, k):
        return meta if k.endswith("meta.json") else {"partes": []}

    monkeypatch.setattr(h, "leer_json_s3", _leer)
    h.handler(_s3_event("texto.json"))
    reg = fake.registros[ID_CAP]
    assert reg["estado"] == EstadoRegistro.SIN_TEXTO.value
    assert "procesado_en" in reg


def test_texto_meta_ausente_es_error(fake, monkeypatch) -> None:
    def _leer(b, k):
        if k.endswith("meta.json"):
            raise ValueError("sin meta")
        return {"texto": "algo"}

    monkeypatch.setattr(h, "leer_json_s3", _leer)
    h.handler(_s3_event("texto.json"))
    assert fake.registros[ID_CAP]["estado"] == EstadoRegistro.ERROR.value
    assert fake.registros[ID_CAP]["error"] == "META_INVALIDA"


def test_texto_procesado(fake, monkeypatch) -> None:
    meta = {"id_educadora": "EDU-0001", "sala_grupo": "SG-A", "fecha_observacion": "2026-10-15"}
    texto = {
        "fuente": "ocr",
        "partes": [
            {"texto": "Pedro apilo bloques", "archivo": "original/foto1.jpg"},
            {"texto": "Hoy frio"},
        ],
    }

    def _leer(b, k):
        return meta if k.endswith("meta.json") else texto

    monkeypatch.setattr(h, "leer_json_s3", _leer)

    vistos: list[tuple[int, str | None]] = []

    def _fake_procesar(entrada, datos, rub, ret, few, *, id_captura, n_parte, archivo_s3):
        vistos.append((n_parte, archivo_s3))
        obs = Observacion(
            id_obs=f"{id_captura}-p{n_parte}-0",
            tipo=TipoObservacion.GENERAL,
            texto_literal=entrada.texto,
            archivo_s3=archivo_s3,
        )
        return Resultado(id_captura=id_captura, observaciones=[obs])

    monkeypatch.setattr(h, "procesar_nota", _fake_procesar)

    resp = h.handler(_s3_event("texto.json"))
    reg = fake.registros[ID_CAP]
    assert reg["estado"] == EstadoRegistro.PROCESADO.value
    assert reg["errores"] == []
    # Dos partes procesadas; la primera con archivo_s3 completo, la segunda sin archivo.
    assert vistos == [(0, f"capturas/{ID_CAP}/original/foto1.jpg"), (1, None)]
    assert resp["procesados"][0]["observaciones"] == 2


def test_texto_una_parte_falla_pero_otra_ok(fake, monkeypatch) -> None:
    from core.modelos import ErrorCaptura
    from core.pipeline import ErrorCapturaExc

    meta = {"id_educadora": "EDU-0001", "sala_grupo": "SG-A", "fecha_observacion": "2026-10-15"}
    texto = {"partes": [{"texto": "ok"}, {"texto": ""}]}

    def _leer(b, k):
        return meta if k.endswith("meta.json") else texto

    monkeypatch.setattr(h, "leer_json_s3", _leer)

    def _fake_procesar(entrada, datos, rub, ret, few, *, id_captura, n_parte, archivo_s3):
        if not entrada.texto.strip():
            raise ErrorCapturaExc(ErrorCaptura.TEXTO_VACIO)
        return Resultado(id_captura=id_captura, observaciones=[])

    monkeypatch.setattr(h, "procesar_nota", _fake_procesar)
    h.handler(_s3_event("texto.json"))
    reg = fake.registros[ID_CAP]
    # Una parte fallo (TEXTO_VACIO) pero la otra ok -> PROCESADO con error en la lista.
    assert reg["estado"] == EstadoRegistro.PROCESADO.value
    assert reg["errores"] == [{"n_parte": 1, "error": "TEXTO_VACIO"}]


def test_texto_sala_desconocida_es_error_total(fake, monkeypatch) -> None:
    from core.modelos import ErrorCaptura
    from core.pipeline import ErrorCapturaExc

    meta = {"id_educadora": "EDU-0001", "sala_grupo": "SG-X", "fecha_observacion": "2026-10-15"}
    texto = {"partes": [{"texto": "a"}, {"texto": "b"}]}

    def _leer(b, k):
        return meta if k.endswith("meta.json") else texto

    monkeypatch.setattr(h, "leer_json_s3", _leer)

    def _fake_procesar(entrada, datos, rub, ret, few, *, id_captura, n_parte, archivo_s3):
        raise ErrorCapturaExc(ErrorCaptura.SALA_DESCONOCIDA)

    monkeypatch.setattr(h, "procesar_nota", _fake_procesar)
    h.handler(_s3_event("texto.json"))
    reg = fake.registros[ID_CAP]
    assert reg["estado"] == EstadoRegistro.ERROR.value
    assert reg["error"] == "SALA_DESCONOCIDA"


# --- ruteo / claves ---

def test_clave_invalida_se_ignora(fake, monkeypatch) -> None:
    monkeypatch.setattr(h, "leer_json_s3", lambda b, k: {})
    event = {
        "Records": [
            {"s3": {"bucket": {"name": BUCKET}, "object": {"key": "capturas/NO-ULID/meta.json"}}}
        ]
    }
    resp = h.handler(event)
    assert resp == {"procesados": []}
    assert fake.registros == {}


def test_objeto_otro_se_ignora(fake, monkeypatch) -> None:
    monkeypatch.setattr(h, "leer_json_s3", lambda b, k: {})
    resp = h.handler(_s3_event("original/foto1.jpg"))
    assert resp == {"procesados": []}
    assert fake.registros == {}


# --- evento directo ---

def test_directo_pasa_id_captura(fake, monkeypatch) -> None:
    capturado: dict[str, Any] = {}

    def _fake_procesar(entrada, datos, rub, ret, few, *, id_captura=None, n_parte=0, archivo_s3=None):
        capturado["id_captura"] = id_captura
        return Resultado(id_captura=id_captura or "CAP-GEN", observaciones=[])

    monkeypatch.setattr(h, "procesar_nota", _fake_procesar)
    event = {
        "texto": "Pedro jugo",
        "id_educadora": "EDU-0001",
        "sala_grupo": "SG-A",
        "fecha": "2026-10-15",
        "id_captura": ID_CAP,
    }
    resp = h.handler(event)
    assert capturado["id_captura"] == ID_CAP
    assert resp["id_captura"] == ID_CAP


def test_directo_evento_invalido(fake) -> None:
    resp = h.handler({"texto": "falta fecha"})
    assert resp["error"]["codigo"] == "ENTRADA_INVALIDA"
