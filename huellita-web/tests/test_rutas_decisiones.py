"""Pruebas de `PUT /api/decisiones`: la regla 7 de punta a punta, sin AWS.

La app de verdad la arma el carril de HTTP (`app.py`); acá se monta solo este ruteador con
los manejadores de error de CONTRATOS.md. Las lecturas y escrituras entran por dobles:
`decisiones.leer_sugerencia` hace de Observaciones, `lectura.leer_registros` de la vista de
la sala y `Tienda` de la tabla Decisiones.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from huellita_api import auth, errores, tiempo
from huellita_api.datos import decisiones, lectura
from huellita_api.modelos import Nino, Registros
from huellita_api.rutas import decisiones as rutas_decisiones
from test_decisiones import (
    CAMBIOS_DISTINTOS,
    CAMBIOS_IGUALES,
    CFG,
    ID_DATASET,
    ID_SUG,
    ORIGINAL_IA,
    SALA_KEY,
    VALIDADA_EN,
    sugerencia,
)

ID_CAPTURA_B = "CAP-01M508E1WXXYXW3KAP0S99M9Z5"
ID_SUG_B = f"{ID_CAPTURA_B}-p0-0"
ID_SUG_SGB = "CAP-01M509QZZ4TPB0K3VJHT4D3XYZ-p0-0"
NINOS = {"SG-A": ("NINO-00253", "NINO-00263", "NINO-00237"), "SG-B": ("NINO-00911",)}

#: Observaciones de la IA: lo que devuelve `decisiones.leer_sugerencia`.
OBSERVACIONES = {
    ID_SUG: sugerencia(),
    ID_SUG_B: sugerencia(
        id=ID_SUG_B,
        evidenciaId=ID_CAPTURA_B,
        ninoId=None,
        nombreDetectado="Martina R.",
        nucleo=None,
        nivel=None,
        conducta=None,
        cita="Hola, Agustín, hoy día levantó una torre.",
        certeza="baja",
    ),
    ID_SUG_SGB: sugerencia(id=ID_SUG_SGB, salaId="SG-B", ninoId="NINO-00911"),
}


@dataclass
class Tienda:
    """Doble de la tabla Decisiones, con lo escrito y lo borrado."""

    escrituras: list[dict] = field(default_factory=list)
    borrados: list[tuple[str, str]] = field(default_factory=list)
    filas: dict[str, dict] = field(default_factory=dict)
    #: en `False`, la consulta de la respuesta todavía no ve lo recién escrito.
    lectura_al_dia: bool = True


class Reloj:
    """Reloj de Chile fijo, para que `validadaEn` sea comparable."""

    def __init__(self) -> None:
        self.momento = datetime(2026, 10, 15, 14, 5, 57, tzinfo=ZoneInfo("America/Santiago"))

    def avanzar(self, segundos: int) -> None:
        self.momento += timedelta(seconds=segundos)


def crear_app() -> FastAPI:
    app = FastAPI()
    rutas_decisiones.configurar(CFG)
    app.include_router(rutas_decisiones.router)  # el router ya trae el prefijo /api

    @app.exception_handler(errores.ErrorApi)
    async def _error_api(_peticion: Request, excepcion: errores.ErrorApi) -> JSONResponse:
        return JSONResponse(
            status_code=errores.estado_http(excepcion.codigo),
            content={"error": {"codigo": excepcion.codigo, "mensaje": excepcion.mensaje}},
        )

    @app.exception_handler(RequestValidationError)
    async def _error_validacion(_peticion: Request, _excepcion: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"codigo": "solicitud_invalida", "mensaje": errores.MENSAJES["solicitud_invalida"]}},
        )

    return app


@pytest.fixture
def api(monkeypatch) -> SimpleNamespace:
    tienda = Tienda()
    reloj = Reloj()

    def _guardar(_cfg: object, sala_key: str, id_sugerencia: str, **datos: object) -> None:
        tienda.escrituras.append({"sala_key": sala_key, "id_sugerencia": id_sugerencia, **datos})
        original = datos.get("original")
        fila = {
            "estado": datos["estado"],
            "validada_por": datos["usuaria_id"],
            "validada_en": datos["validada_en"],
            "nino_id": datos.get("nino_id"),
            "nucleo": datos.get("nucleo"),
            "nivel": datos.get("nivel"),
        }
        if original is not None:
            fila["original"] = {"nino_id": original.ninoId, "nucleo": original.nucleo, "nivel": original.nivel}
        if tienda.lectura_al_dia:
            tienda.filas[id_sugerencia] = fila

    def _borrar(_cfg: object, sala_key: str, id_sugerencia: str) -> None:
        tienda.borrados.append((sala_key, id_sugerencia))
        if tienda.lectura_al_dia:
            tienda.filas.pop(id_sugerencia, None)

    def _leer_ninos(_cfg: object, sala_id: str) -> list[Nino]:
        return [
            Nino(
                id=id_nino,
                nombre=id_nino,
                apellidoInicial="",
                fechaNacimiento="2025-03-01",
                salaId=sala_id,
                activo=True,
            )
            for id_nino in NINOS.get(sala_id, ())
        ]

    def _leer_registros(_cfg: object, sala_id: str, _reloj: object = None) -> Registros:
        sugerencias = []
        for sug in OBSERVACIONES.values():
            if sug.salaId != sala_id:
                continue
            fila = tienda.filas.get(sug.id)
            sugerencias.append(decisiones.aplicar(sug, fila) if fila else sug)
        return Registros(evidencias=[], sugerencias=sugerencias)

    monkeypatch.setattr(decisiones, "leer_sugerencia", lambda _cfg, id_sug: OBSERVACIONES.get(id_sug))
    monkeypatch.setattr(decisiones, "guardar", _guardar)
    monkeypatch.setattr(decisiones, "borrar", _borrar)
    monkeypatch.setattr(lectura, "leer_ninos", _leer_ninos)
    monkeypatch.setattr(lectura, "leer_registros", _leer_registros)
    monkeypatch.setattr(tiempo, "ahora", lambda _cfg: reloj.momento)
    return SimpleNamespace(cliente=TestClient(crear_app()), tienda=tienda, reloj=reloj)


def decidir(api: SimpleNamespace, *items: dict, usuaria: str = "EDU-0001", sala: str = "SG-A", cabecera: str | None = "EDU-0001"):
    cabeceras = {auth.CABECERA_USUARIA: cabecera} if cabecera else {}
    cuerpo = {"salaId": sala, "usuariaId": usuaria, "items": list(items)}
    return api.cliente.put("/api/decisiones", json=cuerpo, headers=cabeceras)


def por_id(respuesta) -> dict[str, dict]:
    return {sug["id"]: sug for sug in respuesta.json()["sugerencias"]}


# --- Las cinco transiciones, por HTTP ------------------------------------------------


def test_confirmar_guarda_la_decision_y_responde_la_sugerencia_aceptada(api) -> None:
    respuesta = decidir(api, {"idSugerencia": ID_SUG, "estado": "aceptada"})
    assert respuesta.status_code == 200
    assert api.tienda.escrituras == [
        {
            "sala_key": SALA_KEY,
            "id_sugerencia": ID_SUG,
            "estado": "aceptada",
            "usuaria_id": "EDU-0001",
            "validada_en": VALIDADA_EN,
            "nino_id": "NINO-00253",
            "nucleo": "lenguaje_comunicacion",
            "nivel": 9,
            "original": None,
        }
    ]
    sug = por_id(respuesta)[ID_SUG]
    assert (sug["estado"], sug["validadaPor"], sug["validadaEn"]) == ("aceptada", "EDU-0001", VALIDADA_EN)
    assert "original" not in sug


def test_corregir_guarda_cambiada_con_el_original_de_la_ia(api) -> None:
    respuesta = decidir(api, {"idSugerencia": ID_SUG, "estado": "aceptada", "cambios": CAMBIOS_DISTINTOS})
    escritura = api.tienda.escrituras[0]
    assert escritura["estado"] == "cambiada"
    assert escritura["original"] == ORIGINAL_IA
    assert (escritura["nino_id"], escritura["nucleo"], escritura["nivel"]) == ("NINO-00263", "cognitivo", 4)
    sug = por_id(respuesta)[ID_SUG]
    assert sug["estado"] == "cambiada"
    assert (sug["ninoId"], sug["nucleo"], sug["nivel"]) == ("NINO-00263", "cognitivo", 4)
    assert sug["original"] == {"ninoId": "NINO-00253", "nucleo": "lenguaje_comunicacion", "nivel": 9}


def test_corregir_con_los_mismos_valores_de_la_ia_queda_aceptada(api) -> None:
    respuesta = decidir(api, {"idSugerencia": ID_SUG, "estado": "aceptada", "cambios": CAMBIOS_IGUALES})
    assert api.tienda.escrituras[0]["estado"] == "aceptada"
    assert api.tienda.escrituras[0]["original"] is None
    assert por_id(respuesta)[ID_SUG]["estado"] == "aceptada"


def test_descartar_guarda_descartada(api) -> None:
    respuesta = decidir(api, {"idSugerencia": ID_SUG, "estado": "descartada"})
    assert api.tienda.escrituras[0]["estado"] == "descartada"
    assert por_id(respuesta)[ID_SUG]["estado"] == "descartada"


def test_dejar_pendiente_borra_la_decision_y_devuelve_los_valores_de_la_ia(api) -> None:
    decidir(api, {"idSugerencia": ID_SUG, "estado": "aceptada", "cambios": CAMBIOS_DISTINTOS})
    api.tienda.escrituras.clear()
    api.tienda.lectura_al_dia = False  # la consulta todavía ve la corrección anterior
    respuesta = decidir(api, {"idSugerencia": ID_SUG, "estado": "pendiente"})
    assert respuesta.status_code == 200
    assert api.tienda.escrituras == []
    assert api.tienda.borrados == [(SALA_KEY, ID_SUG)]
    sug = por_id(respuesta)[ID_SUG]
    assert sug["estado"] == "pendiente"
    assert (sug["ninoId"], sug["nucleo"], sug["nivel"]) == ("NINO-00253", "lenguaje_comunicacion", 9)
    assert "validadaPor" not in sug and "validadaEn" not in sug and "original" not in sug


# --- Respuesta e idempotencia --------------------------------------------------------


def test_responde_todas_las_sugerencias_de_la_sala(api) -> None:
    respuesta = decidir(api, {"idSugerencia": ID_SUG, "estado": "aceptada"})
    sugerencias = respuesta.json()["sugerencias"]
    assert [sug["id"] for sug in sugerencias] == [ID_SUG, ID_SUG_B]  # orden (evidenciaId, id)
    assert por_id(respuesta)[ID_SUG_B]["estado"] == "pendiente"


def test_repetir_la_misma_llamada_da_el_mismo_resultado(api) -> None:
    peticion = {"idSugerencia": ID_SUG, "estado": "aceptada", "cambios": CAMBIOS_DISTINTOS}
    primera = decidir(api, peticion)
    api.reloj.avanzar(90)
    segunda = decidir(api, peticion)
    assert primera.status_code == segunda.status_code == 200
    assert len(api.tienda.filas) == 1
    assert api.tienda.escrituras[0] | {"validada_en": None} == api.tienda.escrituras[1] | {"validada_en": None}
    assert api.tienda.escrituras[1]["validada_en"] == "2026-10-15T14:07:27-03:00"
    sin_marca = [{**sug, "validadaEn": None} for sug in primera.json()["sugerencias"]]
    assert sin_marca == [{**sug, "validadaEn": None} for sug in segunda.json()["sugerencias"]]


def test_la_confirmacion_masiva_manda_todo_en_una_llamada(api) -> None:
    respuesta = decidir(
        api,
        {"idSugerencia": ID_SUG, "estado": "aceptada"},
        {"idSugerencia": ID_SUG_B, "estado": "descartada"},
    )
    assert respuesta.status_code == 200
    assert [escritura["estado"] for escritura in api.tienda.escrituras] == ["aceptada", "descartada"]
    sugerencias = por_id(respuesta)
    assert sugerencias[ID_SUG]["estado"] == "aceptada"
    assert sugerencias[ID_SUG_B]["estado"] == "descartada"


# --- Validaciones de rechazo: nada se escribe ---------------------------------------


def test_un_nino_de_otra_sala_no_escribe_nada(api) -> None:
    cambios = {"ninoId": "NINO-00911", "nucleo": "cognitivo", "nivel": 4}
    respuesta = decidir(api, {"idSugerencia": ID_SUG, "estado": "aceptada", "cambios": cambios})
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "nino_de_otra_sala"
    assert api.tienda.escrituras == []


def test_un_dominio_invalido_es_solicitud_invalida(api) -> None:
    cambios = {"ninoId": "NINO-00253", "nucleo": "psicomotor", "nivel": 4}
    respuesta = decidir(api, {"idSugerencia": ID_SUG, "estado": "aceptada", "cambios": cambios})
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "solicitud_invalida"
    assert api.tienda.escrituras == []


def test_un_nivel_fuera_de_la_rubrica_es_solicitud_invalida(api) -> None:
    cambios = {"ninoId": "NINO-00253", "nucleo": "cognitivo", "nivel": 10}
    respuesta = decidir(api, {"idSugerencia": ID_SUG, "estado": "aceptada", "cambios": cambios})
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "solicitud_invalida"
    assert api.tienda.escrituras == []


def test_un_id_del_dataset_no_es_una_sugerencia_de_la_app(api) -> None:
    respuesta = decidir(api, {"idSugerencia": ID_DATASET, "estado": "aceptada"})
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "sugerencia_desconocida"
    assert api.tienda.escrituras == []


def test_una_sugerencia_de_otra_sala_no_se_decide_desde_esta(api) -> None:
    respuesta = decidir(api, {"idSugerencia": ID_SUG_SGB, "estado": "aceptada"})
    assert respuesta.status_code == 404
    assert api.tienda.escrituras == []


def test_no_escribe_nada_si_un_item_de_la_lista_falla(api) -> None:
    respuesta = decidir(
        api,
        {"idSugerencia": ID_SUG, "estado": "aceptada"},
        {"idSugerencia": ID_DATASET, "estado": "aceptada"},
    )
    assert respuesta.status_code == 404
    assert api.tienda.escrituras == []
    assert api.tienda.borrados == []


def test_la_usuaria_tiene_que_calzar_con_la_cabecera(api) -> None:
    respuesta = decidir(api, {"idSugerencia": ID_SUG, "estado": "aceptada"}, usuaria="EDU-0002")
    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["codigo"] == "sin_acceso"
    assert api.tienda.escrituras == []


def test_sin_cabecera_de_usuaria(api) -> None:
    respuesta = decidir(api, {"idSugerencia": ID_SUG, "estado": "aceptada"}, cabecera=None)
    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["codigo"] == "sin_acceso"


def test_una_sala_que_no_es_de_la_usuaria(api) -> None:
    respuesta = decidir(api, {"idSugerencia": ID_SUG_SGB, "estado": "aceptada"}, sala="SG-B")
    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["codigo"] == "sin_acceso"
    assert api.tienda.escrituras == []


def test_una_lista_vacia_es_solicitud_invalida(api) -> None:
    respuesta = decidir(api)
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "solicitud_invalida"
    assert api.tienda.escrituras == []
