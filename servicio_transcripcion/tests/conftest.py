"""Configuración común: S3 y Transcribe simulados con botocore Stubber. No hay llamadas de red."""
from __future__ import annotations

import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
for _clave, _valor in {"AWS_DEFAULT_REGION": "us-east-1", "AWS_ACCESS_KEY_ID": "prueba", "AWS_SECRET_ACCESS_KEY": "prueba"}.items():
    os.environ.setdefault(_clave, _valor)

import boto3  # noqa: E402
from botocore.response import StreamingBody  # noqa: E402
from botocore.stub import ANY, Stubber  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from jsonschema import Draft202012Validator  # noqa: E402

from transcriptor import servicio as modulo_servicio  # noqa: E402
from transcriptor.app import app  # noqa: E402
from transcriptor.config import Config  # noqa: E402
from transcriptor.servicio import ServicioMock, ServicioTranscribe  # noqa: E402

BUCKET = "bucket-pruebas"
CAPTURAS = "capturas-pruebas"
ID = "tr-CAP-000012"
WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 60
ESQUEMA = json.loads((RAIZ / "contrato" / "resultado_transcripcion.schema.json").read_text(encoding="utf-8"))
CRUDO = json.loads((RAIZ / "src" / "transcriptor" / "datos" / "ejemplo_transcribe.json").read_text(encoding="utf-8"))
_VALIDADOR = Draft202012Validator(ESQUEMA)


def validar(datos: dict) -> dict:
    errores = [error.message for error in _VALIDADOR.iter_errors(datos)]
    assert not errores, errores
    return datos


def ejemplo(nombre: str) -> dict:
    return json.loads((RAIZ / "contrato" / "ejemplos" / f"{nombre}.json").read_text(encoding="utf-8"))


def trabajo(estado: str = "IN_PROGRESS", id_trabajo: str = ID, bucket: str = BUCKET, **extra) -> dict:
    datos = {
        "TranscriptionJobName": id_trabajo,
        "TranscriptionJobStatus": estado,
        "LanguageCode": "es-US",
        "Media": {"MediaFileUri": f"s3://{bucket}/audio/{id_trabajo}.webm"},
        "CreationTime": datetime(2026, 10, 15, 14, 2, 11, tzinfo=timezone.utc),
    }
    if estado in ("COMPLETED", "FAILED"):
        datos["CompletionTime"] = datetime(2026, 10, 15, 14, 2, 38, tzinfo=timezone.utc)
    datos.update(extra)
    return datos


class Aws(SimpleNamespace):
    """Atajos para encolar respuestas simuladas de S3 y Transcribe, en el orden en que se llaman."""

    def trabajo_existe(self, datos: dict) -> None:
        self.transcribe.add_response(
            "get_transcription_job", {"TranscriptionJob": datos}, {"TranscriptionJobName": datos["TranscriptionJobName"]}
        )

    def trabajo_no_existe(self, id_trabajo: str = ID) -> None:
        self.transcribe.add_client_error(
            "get_transcription_job",
            service_error_code="BadRequestException",
            service_message="The requested job couldn't be found. Check the job name and try your request again.",
            http_status_code=400,
            expected_params={"TranscriptionJobName": id_trabajo},
        )

    def objeto(self, clave: str, datos: dict) -> None:
        crudo = json.dumps(datos).encode("utf-8")
        self.s3.add_response(
            "get_object", {"Body": StreamingBody(io.BytesIO(crudo), len(crudo))}, {"Bucket": BUCKET, "Key": clave}
        )

    def objeto_no_existe(self, clave: str) -> None:
        self.s3.add_client_error(
            "get_object", service_error_code="NoSuchKey", http_status_code=404, expected_params={"Bucket": BUCKET, "Key": clave}
        )

    def sube_audio(self, id_trabajo: str = ID) -> None:
        self.s3.add_response(
            "put_object", {}, {"Bucket": BUCKET, "Key": f"audio/{id_trabajo}.webm", "Body": ANY, "ContentType": "audio/webm"}
        )

    def guarda_resultado(self, id_trabajo: str = ID) -> None:
        self.s3.add_response(
            "put_object",
            {},
            {"Bucket": BUCKET, "Key": f"resultados/{id_trabajo}.json", "Body": ANY, "ContentType": "application/json; charset=utf-8"},
        )

    def borra_audio(self, id_trabajo: str = ID) -> None:
        self.s3.add_response("delete_object", {}, {"Bucket": BUCKET, "Key": f"audio/{id_trabajo}.webm"})

    def meta_existe(self, id_captura: str) -> None:
        self.s3.add_response("head_object", {}, {"Bucket": CAPTURAS, "Key": f"capturas/{id_captura}/meta.json"})

    def meta_no_existe(self, id_captura: str) -> None:
        self.s3.add_client_error(
            "head_object",
            service_error_code="404",
            http_status_code=404,
            expected_params={"Bucket": CAPTURAS, "Key": f"capturas/{id_captura}/meta.json"},
        )

    def copia_audio(self, id_captura: str, id_trabajo: str, error: tuple[str, int] | None = None) -> None:
        parametros = {
            "Bucket": CAPTURAS,
            "Key": f"capturas/{id_captura}/original/audio.webm",
            "CopySource": f"{BUCKET}/audio/{id_trabajo}.webm",
        }
        if error:
            self.s3.add_client_error(
                "copy_object", service_error_code=error[0], http_status_code=error[1], expected_params=parametros
            )
        else:
            self.s3.add_response("copy_object", {}, parametros)

    def entrega_texto(
        self, id_captura: str, texto: str, error: tuple[str, int] | None = None, archivo: str | None = "original/audio.webm"
    ) -> None:
        parte = {"texto": texto}
        if archivo:
            parte["archivo"] = archivo
        cuerpo = {"id_captura": id_captura, "fuente": "audio", "partes": [parte]}
        parametros = {
            "Bucket": CAPTURAS,
            "Key": f"capturas/{id_captura}/texto.json",
            "Body": json.dumps(cuerpo, ensure_ascii=False).encode("utf-8"),
            "ContentType": "application/json",
            "IfNoneMatch": "*",
        }
        if error:
            self.s3.add_client_error(
                "put_object", service_error_code=error[0], http_status_code=error[1], expected_params=parametros
            )
        else:
            self.s3.add_response("put_object", {}, parametros)

@pytest.fixture
def aws():
    s3 = boto3.client("s3", region_name="us-east-1")
    transcribe = boto3.client("transcribe", region_name="us-east-1")
    with Stubber(s3) as stub_s3, Stubber(transcribe) as stub_transcribe:
        servicio = ServicioTranscribe(Config(bucket=BUCKET, bucket_capturas=CAPTURAS), s3, transcribe)
        modulo_servicio.configurar_servicio(servicio)
        yield Aws(s3=stub_s3, transcribe=stub_transcribe, servicio=servicio)
        stub_s3.assert_no_pending_responses()
        stub_transcribe.assert_no_pending_responses()
    modulo_servicio.configurar_servicio(None)


@pytest.fixture
def mock():
    modulo_servicio.configurar_servicio(ServicioMock(Config(modo_mock=True)))
    yield
    modulo_servicio.configurar_servicio(None)


@pytest.fixture
def cliente():
    return TestClient(app)