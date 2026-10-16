"""Pruebas de las rutas de lectura con dobles de `datos.lectura` y `datos.audio`: sin AWS."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from huellita_api import auth, errores
from huellita_api.app import app
from huellita_api.config import cargar_config
from huellita_api.modelos import Contexto, Evidencia, Jardin, Nino, Registros, Sala, Sugerencia
from huellita_api.rutas import lectura as rutas

CFG = cargar_config({"JARDIN_DEMO": "JAR-0001", "SALAS_DEMO": "SG-A,SG-B"})

CABECERA_ANA = {auth.CABECERA_USUARIA: "EDU-0001"}
CABECERA_ROSA = {auth.CABECERA_USUARIA: "EDU-0002"}

CONTEXTO = Contexto(
    jardin=Jardin(
        id="JAR-0001",
        nombre="Jardín Sintético Sendero Azul",
        comuna="Arica",
        region="Arica y Parinacota",
    ),
    salas=[
        Sala(id="SG-A", jardinId="JAR-0001", nombre="Sala A", nivelEducativo="Sala Cuna Menor"),
        Sala(id="SG-B", jardinId="JAR-0001", nombre="Sala B", nivelEducativo="Sala Cuna Mayor"),
    ],
    usuarias=auth.usuarias(),
)

NAYARA = Nino(
    id="NIN-0001",
    nombre="Nayara",
    apellidoInicial="",
    fechaNacimiento="2025-03-14",
    salaId="SG-A",
    activo=True,
)
BENJAMIN = Nino(
    id="NIN-0002",
    nombre="Benjamín",
    apellidoInicial="",
    fechaNacimiento="2024-08-02",
    salaId="SG-B",
    activo=True,
)

EVIDENCIA = Evidencia(
    id="CAP-01M503FN5942S3MNAFA14C07AQ",
    salaId="SG-A",
    autorId="EDU-0001",
    creadaEn="2026-10-15T14:05:57-03:00",
    formato="texto",
    estado="procesando",
)
SUGERENCIA = Sugerencia(
    id="OBS-0001-p1",
    evidenciaId="CAP-01M503FN5942S3MNAFA14C07AQ",
    salaId="SG-A",
    tipo="evaluacion",
    cita="Nayara apiló cinco cubos y dijo torre",
    certeza="baja",
    estado="pendiente",
)


class DobleLectura:
    """Doble de `datos.lectura`: anota cada llamada y devuelve lo que se le prepare."""

    def __init__(self, llamadas: list[str]) -> None:
        self.llamadas = llamadas
        self.cfgs: list[Any] = []
        self.contexto = CONTEXTO
        self.ninos: dict[str, list[Nino]] = {"SG-A": [NAYARA], "SG-B": [BENJAMIN]}
        self.registros = Registros(evidencias=[EVIDENCIA], sugerencias=[SUGERENCIA])
        self.explota: Exception | None = None

    def leer_contexto(self, cfg: Any) -> Contexto:
        self._anotar("leer_contexto", cfg)
        return self.contexto

    def leer_ninos(self, cfg: Any, sala_id: str) -> list[Nino]:
        self._anotar(f"leer_ninos:{sala_id}", cfg)
        return self.ninos.get(sala_id, [])

    def leer_registros(self, cfg: Any, sala_id: str, reloj: Any = None) -> Registros:
        self._anotar(f"leer_registros:{sala_id}", cfg)
        return self.registros

    def _anotar(self, llamada: str, cfg: Any) -> None:
        self.llamadas.append(llamada)
        self.cfgs.append(cfg)
        if self.explota is not None:
            raise self.explota


class DobleAudio:
    """Doble de `datos.audio`: solo interesa que se llame antes de leer y que no voltee nada."""

    def __init__(self, llamadas: list[str], explota: Exception | None = None) -> None:
        self.llamadas = llamadas
        self.explota = explota

    def sincronizar(self, cfg: Any, sala_id: str, reloj: Any = None) -> None:
        self.llamadas.append(f"sincronizar:{sala_id}")
        if self.explota is not None:
            raise self.explota


@pytest.fixture
def entorno(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Cliente HTTP con los dos módulos de datos reemplazados por dobles."""
    llamadas: list[str] = []
    lectura = DobleLectura(llamadas)
    audio = DobleAudio(llamadas)
    monkeypatch.setattr(rutas, "dar_config", lambda: CFG)
    monkeypatch.setattr(rutas, "dar_lectura", lambda: lectura)
    monkeypatch.setattr(rutas, "dar_audio", lambda: audio)
    return SimpleNamespace(cliente=TestClient(app), lectura=lectura, audio=audio, llamadas=llamadas)


def codigo_de(respuesta) -> str:
    cuerpo = respuesta.json()
    assert set(cuerpo) == {"error"}
    assert set(cuerpo["error"]) == {"codigo", "mensaje"}
    return cuerpo["error"]["codigo"]


def test_contexto_no_exige_cabecera(entorno: SimpleNamespace) -> None:
    respuesta = entorno.cliente.get("/api/contexto")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["jardin"]["nombre"] == "Jardín Sintético Sendero Azul"
    assert [sala["id"] for sala in cuerpo["salas"]] == ["SG-A", "SG-B"]
    assert [usuaria["id"] for usuaria in cuerpo["usuarias"]] == ["EDU-0001", "EDU-0002"]
    assert entorno.lectura.cfgs == [CFG]


def test_contexto_propaga_el_error_del_lector(entorno: SimpleNamespace) -> None:
    entorno.lectura.explota = errores.error("no_encontrado")
    respuesta = entorno.cliente.get("/api/contexto")
    assert respuesta.status_code == 404
    assert codigo_de(respuesta) == "no_encontrado"


def test_ninos_de_la_sala_de_la_tia(entorno: SimpleNamespace) -> None:
    respuesta = entorno.cliente.get("/api/salas/SG-A/ninos", headers=CABECERA_ANA)
    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {
            "id": "NIN-0001",
            "nombre": "Nayara",
            "apellidoInicial": "",
            "fechaNacimiento": "2025-03-14",
            "salaId": "SG-A",
            "activo": True,
        }
    ]
    assert entorno.llamadas == ["leer_ninos:SG-A"]


def test_ninos_sin_cabecera_no_consulta_nada(entorno: SimpleNamespace) -> None:
    respuesta = entorno.cliente.get("/api/salas/SG-A/ninos")
    assert respuesta.status_code == 403
    assert codigo_de(respuesta) == "sin_acceso"
    assert entorno.llamadas == []


def test_ninos_con_autora_desconocida(entorno: SimpleNamespace) -> None:
    respuesta = entorno.cliente.get(
        "/api/salas/SG-A/ninos", headers={auth.CABECERA_USUARIA: "EDU-9999"}
    )
    assert respuesta.status_code == errores.estado_http("autora_desconocida")
    assert codigo_de(respuesta) == "autora_desconocida"
    assert entorno.llamadas == []


def test_ninos_de_sala_fuera_de_la_demo(entorno: SimpleNamespace) -> None:
    respuesta = entorno.cliente.get("/api/salas/SG-Z/ninos", headers=CABECERA_ANA)
    assert respuesta.status_code == 404
    assert codigo_de(respuesta) == "sala_desconocida"
    assert entorno.llamadas == []


def test_ninos_de_la_sala_de_otra_tia(entorno: SimpleNamespace) -> None:
    respuesta = entorno.cliente.get("/api/salas/SG-A/ninos", headers=CABECERA_ROSA)
    assert respuesta.status_code == 403
    assert codigo_de(respuesta) == "sin_acceso"
    assert entorno.llamadas == []


def test_un_nino_de_la_sala_de_la_tia(entorno: SimpleNamespace) -> None:
    respuesta = entorno.cliente.get("/api/ninos/NIN-0001", headers=CABECERA_ANA)
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Nayara"


def test_un_nino_inexistente_responde_no_encontrado(entorno: SimpleNamespace) -> None:
    respuesta = entorno.cliente.get("/api/ninos/NIN-9999", headers=CABECERA_ANA)
    assert respuesta.status_code == 404
    assert codigo_de(respuesta) == "no_encontrado"


def test_un_nino_de_otra_sala_no_existe_para_la_tia(entorno: SimpleNamespace) -> None:
    respuesta = entorno.cliente.get("/api/ninos/NIN-0002", headers=CABECERA_ANA)
    assert respuesta.status_code == 404
    assert codigo_de(respuesta) == "no_encontrado"
    assert entorno.llamadas == ["leer_ninos:SG-A"]


def test_un_nino_usa_leer_nino_si_el_carril_la_expone(entorno: SimpleNamespace) -> None:
    entorno.lectura.leer_nino = lambda cfg, id_nino: NAYARA if id_nino == NAYARA.id else None
    respuesta = entorno.cliente.get("/api/ninos/NIN-0001", headers=CABECERA_ANA)
    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == "NIN-0001"
    assert entorno.llamadas == []
    ajeno = entorno.cliente.get("/api/ninos/NIN-0002", headers=CABECERA_ANA)
    assert ajeno.status_code == 404
    assert codigo_de(ajeno) == "no_encontrado"


def test_un_nino_propaga_el_no_encontrado_del_lector(entorno: SimpleNamespace) -> None:
    def leer_nino(cfg: Any, id_nino: str) -> Nino:
        raise errores.error("no_encontrado")

    entorno.lectura.leer_nino = leer_nino
    respuesta = entorno.cliente.get("/api/ninos/NIN-9999", headers=CABECERA_ANA)
    assert respuesta.status_code == 404
    assert codigo_de(respuesta) == "no_encontrado"


def test_un_nino_sin_cabecera_responde_sin_acceso(entorno: SimpleNamespace) -> None:
    respuesta = entorno.cliente.get("/api/ninos/NIN-0001")
    assert respuesta.status_code == 403
    assert codigo_de(respuesta) == "sin_acceso"


def test_registros_sincroniza_el_audio_antes_de_leer(entorno: SimpleNamespace) -> None:
    respuesta = entorno.cliente.get("/api/salas/SG-A/registros", headers=CABECERA_ANA)
    assert respuesta.status_code == 200
    assert entorno.llamadas == ["sincronizar:SG-A", "leer_registros:SG-A"]
    cuerpo = respuesta.json()
    assert [evidencia["id"] for evidencia in cuerpo["evidencias"]] == [EVIDENCIA.id]
    assert [sugerencia["id"] for sugerencia in cuerpo["sugerencias"]] == [SUGERENCIA.id]


def test_registros_responde_igual_si_falla_la_sincronizacion(entorno: SimpleNamespace) -> None:
    entorno.audio.explota = RuntimeError("el transcriptor no contestó")
    respuesta = entorno.cliente.get("/api/salas/SG-A/registros", headers=CABECERA_ANA)
    assert respuesta.status_code == 200
    assert entorno.llamadas == ["sincronizar:SG-A", "leer_registros:SG-A"]


def test_registros_sin_cabecera_no_sincroniza(entorno: SimpleNamespace) -> None:
    respuesta = entorno.cliente.get("/api/salas/SG-A/registros")
    assert respuesta.status_code == 403
    assert codigo_de(respuesta) == "sin_acceso"
    assert entorno.llamadas == []


def test_registros_omite_los_campos_en_none(entorno: SimpleNamespace) -> None:
    respuesta = entorno.cliente.get("/api/salas/SG-A/registros", headers=CABECERA_ANA)
    evidencia = respuesta.json()["evidencias"][0]
    sugerencia = respuesta.json()["sugerencias"][0]
    assert set(evidencia) == {"id", "salaId", "autorId", "creadaEn", "formato", "estado"}
    assert "ninoId" not in sugerencia
    assert "original" not in sugerencia
    assert sugerencia["cita"] == SUGERENCIA.cita


def test_registros_mantiene_el_orden_que_entrega_el_lector(entorno: SimpleNamespace) -> None:
    primera = EVIDENCIA.model_copy(update={"id": "CAP-UNO", "creadaEn": "2026-10-15T09:00:00-03:00"})
    segunda = EVIDENCIA.model_copy(update={"id": "CAP-DOS", "creadaEn": "2026-10-15T14:05:57-03:00"})
    entorno.lectura.registros = Registros(evidencias=[primera, segunda], sugerencias=[])
    respuesta = entorno.cliente.get("/api/salas/SG-A/registros", headers=CABECERA_ANA)
    assert [evidencia["id"] for evidencia in respuesta.json()["evidencias"]] == ["CAP-UNO", "CAP-DOS"]
