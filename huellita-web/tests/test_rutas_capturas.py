"""Pruebas de `POST /api/capturas` y `POST /api/capturas/{id}/archivar`.

Monta el router sobre una app igual a la del carril HTTP (manejadores de
`ErrorApi` y de validación) y usa los dobles de `test_capturas`: ni S3 ni
DynamoDB ni el transcriptor se tocan de verdad.
"""
from __future__ import annotations

import base64
import importlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from huellita_api import s3, ulid
from huellita_api.config import Config
from test_capturas import Almacen, cfg_de_prueba, instalar_dobles_de_rutas

instalar_dobles_de_rutas()

rutas_capturas = importlib.import_module("huellita_api.rutas.capturas")
capturas = importlib.import_module("huellita_api.datos.capturas")
errores = importlib.import_module("huellita_api.errores")
tiempo = importlib.import_module("huellita_api.tiempo")
audio = importlib.import_module("huellita_api.datos.audio")

CABECERA = {"X-Usuaria-Id": "EDU-0001"}
TEXTO = "Nayara apiló cinco cubos y dijo torre"
MOMENTO = datetime(2026, 10, 15, 14, 5, 57, tzinfo=ZoneInfo("America/Santiago"))
CREADA_EN = "2026-10-15T14:05:57-03:00"
DIA = "2026-10-15"


class FalsoS3:
    """Cliente de S3 de mentira: anota las claves y puede fallar en una de ellas."""

    def __init__(self) -> None:
        self.claves: list[str] = []
        self.cuerpos: dict[str, dict] = {}
        self.falla_en: str | None = None

    def put_object(self, **parametros: object) -> dict:
        clave = str(parametros["Key"])
        if self.falla_en and clave.endswith(self.falla_en):
            raise RuntimeError("S3 no responde")
        self.claves.append(clave)
        self.cuerpos[clave] = dict(parametros)
        return {}

    def cuerpo(self, sufijo: str) -> dict:
        clave = next(clave for clave in self.claves if clave.endswith(sufijo))
        return json.loads(self.cuerpos[clave]["Body"].decode("utf-8"))


@dataclass
class Entorno:
    """Lo que necesita cada prueba de ruta."""

    cliente: TestClient
    almacen: Almacen
    s3: FalsoS3
    cfg: Config
    enviados: list[tuple[str, str]] = field(default_factory=list)


def _app() -> FastAPI:
    """App mínima con los mismos manejadores de error que `app.py`."""
    app = FastAPI()
    app.include_router(rutas_capturas.router)  # el router ya trae el prefijo /api

    @app.exception_handler(errores.ErrorApi)
    async def _api(_peticion, excepcion):  # noqa: ANN202 - firma de starlette
        return JSONResponse(
            status_code=errores.estado_http(excepcion.codigo),
            content={"error": {"codigo": excepcion.codigo, "mensaje": excepcion.mensaje}},
        )

    @app.exception_handler(RequestValidationError)
    async def _invalida(_peticion, _excepcion):  # noqa: ANN202 - firma de starlette
        return JSONResponse(
            status_code=422,
            content={"error": {"codigo": "solicitud_invalida", "mensaje": "No pudimos entender esto."}},
        )

    return app


@pytest.fixture
def entorno(monkeypatch: pytest.MonkeyPatch) -> Entorno:
    cfg = cfg_de_prueba()
    almacen = Almacen()
    almacen.conectar(monkeypatch)
    falso_s3 = FalsoS3()
    monkeypatch.setattr(s3, "cliente", lambda: falso_s3)
    monkeypatch.setattr(rutas_capturas, "CFG", cfg)
    return Entorno(TestClient(_app()), almacen, falso_s3, cfg)


@pytest.fixture
def reloj_fijo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deja la hora de Chile quieta para comparar cuerpos exactos."""
    monkeypatch.setattr(tiempo, "ahora", lambda _cfg: MOMENTO)


@pytest.fixture
def envio_de_audio(monkeypatch: pytest.MonkeyPatch, entorno: Entorno) -> Entorno:
    """Doble de `datos/audio.enviar`: guarda el trabajo como lo haría el carril
    de audio, sin llamar al transcriptor."""

    def enviar(cfg: Config, id_captura: str, audio_base64: str) -> str:
        entorno.enviados.append((id_captura, audio_base64))
        id_trabajo = f"tr-{id_captura}"
        capturas.marcar_envio(cfg, id_captura, "enviada", id_trabajo=id_trabajo)
        return id_trabajo

    monkeypatch.setattr(audio, "enviar", enviar)
    return entorno


def cuerpo(**extra: object) -> dict:
    """Cuerpo de `POST /api/capturas` con formato texto."""
    base: dict = {"salaId": "SG-A", "autorId": "EDU-0001", "formato": "texto", "texto": TEXTO}
    base.update(extra)
    return base


def audio_base64(bytes_crudos: int = 32) -> str:
    return base64.b64encode(b"\x00" * bytes_crudos).decode("ascii")


def fila(entorno: Entorno, id_captura: str) -> dict:
    return entorno.almacen.fila(entorno.cfg.tabla_capturas, id_captura)


def test_la_nota_de_texto_responde_201_con_la_evidencia_en_procesando(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post("/api/capturas", json=cuerpo(), headers=CABECERA)

    assert respuesta.status_code == 201
    evidencia = respuesta.json()["evidencia"]
    assert ulid.es_id_captura(evidencia["id"])
    assert evidencia["salaId"] == "SG-A"
    assert evidencia["autorId"] == "EDU-0001"
    assert evidencia["formato"] == "texto"
    assert evidencia["estado"] == "procesando"
    assert evidencia["textoExtraido"] == TEXTO
    assert "foto" not in evidencia  # los campos vacíos no viajan


def test_meta_json_se_escribe_antes_que_texto_json_con_los_cuerpos_exactos(
    entorno: Entorno, reloj_fijo: None
) -> None:
    respuesta = entorno.cliente.post("/api/capturas", json=cuerpo(), headers=CABECERA)

    id_captura = respuesta.json()["evidencia"]["id"]
    assert entorno.s3.claves == [
        f"capturas/{id_captura}/meta.json",
        f"capturas/{id_captura}/texto.json",
    ]
    assert entorno.s3.cuerpo("meta.json") == {
        "id_educadora": "EDU-0001",
        "sala_grupo": "SG-A",
        "fecha_observacion": DIA,
    }
    assert entorno.s3.cuerpo("texto.json") == {
        "id_captura": id_captura,
        "fuente": "manual",
        "partes": [{"texto": TEXTO}],
    }
    assert entorno.s3.cuerpos[entorno.s3.claves[0]]["ContentType"] == "application/json"


def test_la_fecha_de_meta_json_es_la_de_chile(entorno: Entorno) -> None:
    entorno.cliente.post("/api/capturas", json=cuerpo(), headers=CABECERA)

    hoy_en_chile = datetime.now(ZoneInfo("America/Santiago")).date().isoformat()
    assert entorno.s3.cuerpo("meta.json")["fecha_observacion"] == hoy_en_chile


def test_la_fila_queda_enviada_con_el_texto_y_la_sala(entorno: Entorno, reloj_fijo: None) -> None:
    respuesta = entorno.cliente.post(
        "/api/capturas", json=cuerpo(ninoIdSugerido="NIN-0003"), headers=CABECERA
    )

    item = fila(entorno, respuesta.json()["evidencia"]["id"])
    assert item["estado_envio"] == {"S": "enviada"}
    assert item["sala_key"] == {"S": "JAR-0001#SG-A"}
    assert item["sala_grupo"] == {"S": "SG-A"}
    assert item["id_jardin"] == {"S": "JAR-0001"}
    assert item["creada_en"] == {"S": CREADA_EN}
    assert item["texto_extraido"] == {"S": TEXTO}
    assert item["nino_id_sugerido"] == {"S": "NIN-0003"}
    assert "estado_final" not in item


def test_el_texto_se_guarda_recortado(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post("/api/capturas", json=cuerpo(texto=f"  {TEXTO}  "), headers=CABECERA)

    assert respuesta.json()["evidencia"]["textoExtraido"] == TEXTO
    assert entorno.s3.cuerpo("texto.json")["partes"] == [{"texto": TEXTO}]


@pytest.mark.parametrize("formato", ["foto", "video", "TEXTO", ""])
def test_foto_u_otro_formato_responde_422(entorno: Entorno, formato: str) -> None:
    respuesta = entorno.cliente.post("/api/capturas", json=cuerpo(formato=formato), headers=CABECERA)

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "formato_no_soportado"
    assert entorno.s3.claves == []


@pytest.mark.parametrize("texto", ["", "   ", "\n\t "])
def test_el_texto_vacio_responde_422(entorno: Entorno, texto: str) -> None:
    respuesta = entorno.cliente.post("/api/capturas", json=cuerpo(texto=texto), headers=CABECERA)

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "texto_invalido"
    assert entorno.almacen.tablas == {}


def test_el_texto_sin_enviar_responde_422(entorno: Entorno) -> None:
    sin_texto = cuerpo()
    del sin_texto["texto"]

    respuesta = entorno.cliente.post("/api/capturas", json=sin_texto, headers=CABECERA)

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "texto_invalido"


def test_el_texto_de_mas_de_5000_caracteres_responde_422(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post("/api/capturas", json=cuerpo(texto="a" * 5001), headers=CABECERA)

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "texto_invalido"


def test_el_texto_de_5000_caracteres_todavia_sirve(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post("/api/capturas", json=cuerpo(texto="a" * 5000), headers=CABECERA)

    assert respuesta.status_code == 201


def test_el_tope_diario_responde_429(monkeypatch: pytest.MonkeyPatch, entorno: Entorno) -> None:
    monkeypatch.setattr(rutas_capturas, "CFG", cfg_de_prueba(MAX_CAPTURAS_DIA="2"))

    primera = entorno.cliente.post("/api/capturas", json=cuerpo(), headers=CABECERA)
    segunda = entorno.cliente.post("/api/capturas", json=cuerpo(), headers=CABECERA)
    tercera = entorno.cliente.post("/api/capturas", json=cuerpo(), headers=CABECERA)

    assert [primera.status_code, segunda.status_code] == [201, 201]
    assert tercera.status_code == 429
    assert tercera.json()["error"]["codigo"] == "tope_diario"
    assert len(entorno.s3.claves) == 4  # dos objetos por captura aceptada


def test_un_campo_extra_en_el_cuerpo_responde_solicitud_invalida(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post("/api/capturas", json=cuerpo(sobra="x"), headers=CABECERA)

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "solicitud_invalida"


def test_sin_cabecera_de_usuaria_responde_sin_acceso(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post("/api/capturas", json=cuerpo())

    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["codigo"] == "sin_acceso"


def test_una_cabecera_desconocida_responde_autora_desconocida(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post(
        "/api/capturas", json=cuerpo(), headers={"X-Usuaria-Id": "EDU-9999"}
    )

    assert respuesta.status_code == 422  # tía inexistente (SPEC-OFICIAL §1)
    assert respuesta.json()["error"]["codigo"] == "autora_desconocida"


def test_una_tia_inexistente_en_el_cuerpo_responde_422(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post("/api/capturas", json=cuerpo(autorId="EDU-9999"), headers=CABECERA)

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "autora_desconocida"


def test_un_autor_distinto_de_la_cabecera_responde_sin_acceso(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post("/api/capturas", json=cuerpo(autorId="EDU-0002"), headers=CABECERA)

    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["codigo"] == "sin_acceso"


def test_una_sala_fuera_de_salas_demo_responde_404(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post("/api/capturas", json=cuerpo(salaId="SG-Z"), headers=CABECERA)

    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "sala_desconocida"


def test_la_sala_de_otra_tia_responde_sin_acceso(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post("/api/capturas", json=cuerpo(salaId="SG-B"), headers=CABECERA)

    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["codigo"] == "sin_acceso"


def test_si_falla_meta_json_la_fila_queda_en_error_envio(entorno: Entorno) -> None:
    entorno.s3.falla_en = "meta.json"

    respuesta = entorno.cliente.post("/api/capturas", json=cuerpo(), headers=CABECERA)

    assert respuesta.status_code == 502
    assert respuesta.json()["error"]["codigo"] == "error_envio"
    assert entorno.s3.claves == []  # texto.json no se escribe
    (item,) = [fila for fila in entorno.almacen.filas(entorno.cfg.tabla_capturas).values() if "sala_key" in fila]
    assert item["estado_envio"] == {"S": "error_envio"}


def test_si_falla_texto_json_la_fila_queda_en_error_envio(entorno: Entorno) -> None:
    entorno.s3.falla_en = "texto.json"

    respuesta = entorno.cliente.post("/api/capturas", json=cuerpo(), headers=CABECERA)

    assert respuesta.status_code == 502
    assert respuesta.json()["error"]["codigo"] == "error_envio"
    assert [clave.rsplit("/", 1)[-1] for clave in entorno.s3.claves] == ["meta.json"]
    (item,) = [fila for fila in entorno.almacen.filas(entorno.cfg.tabla_capturas).values() if "sala_key" in fila]
    assert item["estado_envio"] == {"S": "error_envio"}
    assert "estado_final" not in item


def test_el_audio_escribe_meta_json_y_deja_el_trabajo_del_transcriptor(envio_de_audio: Entorno) -> None:
    entorno = envio_de_audio
    b64 = audio_base64()

    respuesta = entorno.cliente.post(
        "/api/capturas",
        json={
            "salaId": "SG-A",
            "autorId": "EDU-0001",
            "formato": "audio",
            "audioBase64": b64,
            "mimeType": "audio/webm",
        },
        headers=CABECERA,
    )

    assert respuesta.status_code == 201
    evidencia = respuesta.json()["evidencia"]
    assert evidencia["formato"] == "audio"
    assert evidencia["estado"] == "procesando"
    assert "textoExtraido" not in evidencia
    id_captura = evidencia["id"]
    assert [clave.rsplit("/", 1)[-1] for clave in entorno.s3.claves] == ["meta.json"]
    assert entorno.enviados == [(id_captura, b64)]
    item = fila(entorno, id_captura)
    assert item["id_trabajo"] == {"S": f"tr-{id_captura}"}
    assert item["estado_envio"] == {"S": "enviada"}
    assert item["mime_type"] == {"S": "audio/webm"}


def test_el_audio_de_mas_de_4_mib_responde_413(entorno: Entorno) -> None:
    grande = base64.b64encode(b"\x00" * (audio.MAX_BYTES_AUDIO + 1)).decode("ascii")

    respuesta = entorno.cliente.post(
        "/api/capturas",
        json={"salaId": "SG-A", "autorId": "EDU-0001", "formato": "audio", "audioBase64": grande},
        headers=CABECERA,
    )

    assert respuesta.status_code == 413
    assert respuesta.json()["error"]["codigo"] == "audio_demasiado_grande"
    assert entorno.almacen.tablas == {}  # ni fila ni cupo del día


def test_el_audio_de_4_mib_justos_sirve(envio_de_audio: Entorno) -> None:
    justo = base64.b64encode(b"\x00" * audio.MAX_BYTES_AUDIO).decode("ascii")

    respuesta = envio_de_audio.cliente.post(
        "/api/capturas",
        json={"salaId": "SG-A", "autorId": "EDU-0001", "formato": "audio", "audioBase64": justo},
        headers=CABECERA,
    )

    assert respuesta.status_code == 201


@pytest.mark.parametrize("valor", ["no-es-base64!!", "QQ", "###"])
def test_el_base64_invalido_responde_422(entorno: Entorno, valor: str) -> None:
    respuesta = entorno.cliente.post(
        "/api/capturas",
        json={"salaId": "SG-A", "autorId": "EDU-0001", "formato": "audio", "audioBase64": valor},
        headers=CABECERA,
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "base64_invalido"


def test_el_audio_sin_contenido_responde_422(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post(
        "/api/capturas",
        json={"salaId": "SG-A", "autorId": "EDU-0001", "formato": "audio"},
        headers=CABECERA,
    )

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "base64_invalido"


@pytest.mark.parametrize(
    ("codigo", "estado"),
    [
        ("servicio_saturado", 503),
        ("audio_demasiado_grande", 413),
        ("formato_audio_no_soportado", 415),
        ("transcriptor_caido", 502),
    ],
)
def test_los_errores_del_transcriptor_se_traducen(
    monkeypatch: pytest.MonkeyPatch, entorno: Entorno, codigo: str, estado: int
) -> None:
    def enviar(cfg: Config, id_captura: str, _audio_base64: str) -> str:
        capturas.marcar_envio(cfg, id_captura, "error_envio")
        raise errores.error(codigo)

    monkeypatch.setattr(audio, "enviar", enviar)

    respuesta = entorno.cliente.post(
        "/api/capturas",
        json={"salaId": "SG-A", "autorId": "EDU-0001", "formato": "audio", "audioBase64": audio_base64()},
        headers=CABECERA,
    )

    assert respuesta.status_code == estado
    assert respuesta.json()["error"]["codigo"] == codigo
    (item,) = [fila for fila in entorno.almacen.filas(entorno.cfg.tabla_capturas).values() if "sala_key" in fila]
    assert item["estado_envio"] == {"S": "error_envio"}


def test_archivar_responde_204_y_deja_la_captura_lista(entorno: Entorno) -> None:
    creada = entorno.cliente.post("/api/capturas", json=cuerpo(), headers=CABECERA)
    id_captura = creada.json()["evidencia"]["id"]

    respuesta = entorno.cliente.post(
        f"/api/capturas/{id_captura}/archivar", json={"salaId": "SG-A"}, headers=CABECERA
    )

    assert respuesta.status_code == 204
    assert respuesta.content == b""
    item = fila(entorno, id_captura)
    assert item["archivada"] == {"BOOL": True}
    assert item["estado_final"] == {"S": "lista"}


def test_archivar_es_idempotente(entorno: Entorno) -> None:
    creada = entorno.cliente.post("/api/capturas", json=cuerpo(), headers=CABECERA)
    id_captura = creada.json()["evidencia"]["id"]
    ruta = f"/api/capturas/{id_captura}/archivar"

    primera = entorno.cliente.post(ruta, json={"salaId": "SG-A"}, headers=CABECERA)
    segunda = entorno.cliente.post(ruta, json={"salaId": "SG-A"}, headers=CABECERA)

    assert [primera.status_code, segunda.status_code] == [204, 204]


def test_archivar_una_captura_de_otra_sala_responde_404(entorno: Entorno) -> None:
    creada = entorno.cliente.post("/api/capturas", json=cuerpo(), headers=CABECERA)
    id_captura = creada.json()["evidencia"]["id"]

    respuesta = entorno.cliente.post(
        f"/api/capturas/{id_captura}/archivar",
        json={"salaId": "SG-B"},
        headers={"X-Usuaria-Id": "EDU-0002"},
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "no_encontrado"
    assert "archivada" not in fila(entorno, id_captura)


def test_archivar_una_captura_que_no_existe_responde_404(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post(
        "/api/capturas/CAP-01M503FN5942S3MNAFA14C07AQ/archivar",
        json={"salaId": "SG-A"},
        headers=CABECERA,
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "no_encontrado"


def test_archivar_sin_cabecera_responde_sin_acceso(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post(
        "/api/capturas/CAP-01M503FN5942S3MNAFA14C07AQ/archivar", json={"salaId": "SG-A"}
    )

    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["codigo"] == "sin_acceso"
