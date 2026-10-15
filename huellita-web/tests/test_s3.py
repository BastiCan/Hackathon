"""Pruebas de las escrituras en S3: claves, cuerpos exactos y JSON UTF-8 (§7)."""
from __future__ import annotations

import json

import pytest

from huellita_api import s3
from huellita_api.config import Config, cargar_config

ID = "CAP-01M503FN5942S3MNAFA14C07AQ"


class FalsoS3:
    """Cliente de S3 de mentira: anota cada `put_object` y nunca sale a la red."""

    def __init__(self, falla_en: str | None = None) -> None:
        self.puestos: list[dict] = []
        self.falla_en = falla_en

    def put_object(self, **parametros: object) -> dict:
        self.puestos.append(parametros)
        clave = str(parametros["Key"])
        if self.falla_en and clave.endswith(self.falla_en):
            raise RuntimeError("S3 no responde")
        return {}


@pytest.fixture
def cfg() -> Config:
    return cargar_config({"BUCKET_CAPTURAS": "integra-capturas-test"})


@pytest.fixture
def falso(monkeypatch: pytest.MonkeyPatch) -> FalsoS3:
    doble = FalsoS3()
    monkeypatch.setattr(s3, "cliente", lambda: doble)
    return doble


def test_las_claves_llevan_el_prefijo_de_capturas() -> None:
    assert s3.clave_meta(ID) == f"capturas/{ID}/meta.json"
    assert s3.clave_texto(ID) == f"capturas/{ID}/texto.json"


def test_meta_json_lleva_exactamente_tres_claves_en_orden() -> None:
    cuerpo = s3.cuerpo_meta("EDU-0001", "SG-A", "2026-10-15")

    assert cuerpo == {"id_educadora": "EDU-0001", "sala_grupo": "SG-A", "fecha_observacion": "2026-10-15"}
    assert list(cuerpo) == ["id_educadora", "sala_grupo", "fecha_observacion"]


def test_texto_json_lleva_exactamente_tres_claves() -> None:
    cuerpo = s3.cuerpo_texto(ID, "Nayara apiló cinco cubos y dijo torre")

    assert cuerpo == {
        "id_captura": ID,
        "fuente": "manual",
        "partes": [{"texto": "Nayara apiló cinco cubos y dijo torre"}],
    }
    assert list(cuerpo) == ["id_captura", "fuente", "partes"]


def test_la_fuente_del_audio_se_puede_pedir() -> None:
    assert s3.cuerpo_texto(ID, "lo transcrito", "audio")["fuente"] == "audio"


def test_subir_json_usa_el_bucket_el_tipo_y_utf8(cfg: Config, falso: FalsoS3) -> None:
    s3.subir_json(cfg, s3.clave_texto(ID), s3.cuerpo_texto(ID, "apiló la torre"))

    (puesto,) = falso.puestos
    assert puesto["Bucket"] == "integra-capturas-test"
    assert puesto["Key"] == f"capturas/{ID}/texto.json"
    assert puesto["ContentType"] == "application/json"
    assert isinstance(puesto["Body"], bytes)
    assert "apiló".encode("utf-8") in puesto["Body"]  # UTF-8 de verdad, sin \u escapado
    assert b"\\u" not in puesto["Body"]
    assert json.loads(puesto["Body"].decode("utf-8")) == s3.cuerpo_texto(ID, "apiló la torre")


def test_el_error_de_s3_se_propaga_tal_cual(cfg: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(s3, "cliente", lambda: FalsoS3(falla_en="meta.json"))

    with pytest.raises(RuntimeError):
        s3.subir_json(cfg, s3.clave_meta(ID), s3.cuerpo_meta("EDU-0001", "SG-A", "2026-10-15"))


def test_los_clientes_boto3_traen_los_tiempos_limite_del_spec() -> None:
    assert s3.AJUSTES.connect_timeout == 3
    assert s3.AJUSTES.read_timeout == 8
    assert s3.AJUSTES.retries == {"mode": "standard"}
