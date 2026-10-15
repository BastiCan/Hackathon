"""Rutas de lectura del BFF: salud, contexto, niños/as y registros de una sala.

Los datos los arma `huellita_api.datos.lectura` y las transcripciones las pone al día
`huellita_api.datos.audio`. Los dos se alcanzan por `dar_lectura()` y `dar_audio()`, que las
pruebas reemplazan por dobles para no tocar AWS.
"""
from __future__ import annotations

import logging
from types import ModuleType
from typing import Annotated, Any

from fastapi import APIRouter, Header

from huellita_api import auth, errores
from huellita_api.config import Config
from huellita_api.datos import audio as datos_audio
from huellita_api.datos import lectura as datos_lectura
from huellita_api.modelos import Contexto, Nino, Registros, Usuaria
from huellita_api.rutas import PREFIJO

router = APIRouter(prefix=PREFIJO, tags=["lectura"])

_LOG = logging.getLogger(__name__)

#: Cabecera con el id de la tía. Las rutas de salud y contexto no la piden.
CabeceraUsuaria = Annotated[str | None, Header(alias=auth.CABECERA_USUARIA)]


def dar_config() -> Config:
    """La `Config` que `app.py` leyó una sola vez al importarse."""
    from huellita_api.app import CFG

    return CFG


def dar_lectura() -> Any:
    """Módulo `datos.lectura`, que es quien habla con DynamoDB."""
    return datos_lectura


def dar_audio() -> ModuleType:
    """Módulo `datos.audio`, que es quien habla con el transcriptor."""
    return datos_audio


@router.get("/salud")
def salud() -> dict[str, str]:
    """Latido del BFF: responde sin consultar AWS."""
    return {"estado": "ok"}


@router.get("/contexto", response_model=Contexto, response_model_exclude_none=True)
def contexto() -> Contexto:
    """Jardín, salas y tías de la demo. Sin cabecera: la app la necesita para elegir usuaria."""
    return dar_lectura().leer_contexto(dar_config())


@router.get("/salas/{sala_id}/ninos", response_model=list[Nino], response_model_exclude_none=True)
def ninos_de_sala(sala_id: str, id_usuaria: CabeceraUsuaria = None) -> list[Nino]:
    """Los niños/as de una sala de la tía, en orden alfabético."""
    cfg = dar_config()
    usuaria = auth.usuaria_o_error(id_usuaria)
    auth.exigir_sala(cfg, usuaria, sala_id)
    return dar_lectura().leer_ninos(cfg, sala_id)


@router.get("/ninos/{id_nino}", response_model=Nino, response_model_exclude_none=True)
def nino(id_nino: str, id_usuaria: CabeceraUsuaria = None) -> Nino:
    """Un niño/a de las salas de la tía. Si no está en ninguna responde `no_encontrado`."""
    cfg = dar_config()
    usuaria = auth.usuaria_o_error(id_usuaria)
    encontrado = _buscar_nino(cfg, dar_lectura(), usuaria, id_nino)
    if encontrado is None:
        raise errores.error("no_encontrado")
    return encontrado


@router.get("/salas/{sala_id}/registros", response_model=Registros, response_model_exclude_none=True)
def registros_de_sala(sala_id: str, id_usuaria: CabeceraUsuaria = None) -> Registros:
    """Evidencias (por `creadaEn` ascendente) y sugerencias de la sala. La app la consulta cada 5 s."""
    cfg = dar_config()
    usuaria = auth.usuaria_o_error(id_usuaria)
    auth.exigir_sala(cfg, usuaria, sala_id)
    _sincronizar_audio(cfg, sala_id)
    return dar_lectura().leer_registros(cfg, sala_id)


def _salas_visibles(cfg: Config, usuaria: Usuaria) -> list[str]:
    """Las salas de la demo que son de la tía, en el orden de la configuración."""
    return [sala for sala in cfg.salas if sala in usuaria.salaIds]


def _buscar_nino(cfg: Config, lectura: Any, usuaria: Usuaria, id_nino: str) -> Nino | None:
    """Busca al niño/a solo en las salas de la tía: lo de otras salas no existe para ella.

    Usa `lectura.leer_nino` si su carril la expone; si no, compone `leer_nino` a mano con
    `leer_ninos`, que es la única función de búsqueda que fija el contrato.
    """
    salas = _salas_visibles(cfg, usuaria)
    leer_nino = getattr(lectura, "leer_nino", None)
    if leer_nino is not None:
        encontrado = leer_nino(cfg, id_nino)
        if encontrado is None or encontrado.salaId not in salas:
            return None
        return encontrado
    for sala in salas:
        for candidato in lectura.leer_ninos(cfg, sala):
            if candidato.id == id_nino:
                return candidato
    return None


def _sincronizar_audio(cfg: Config, sala_id: str) -> None:
    """Pone al día las transcripciones antes de leer. Si falla, la respuesta sigue igual."""
    try:
        dar_audio().sincronizar(cfg, sala_id)
    except Exception:  # noqa: BLE001 - sincronizar nunca puede voltear /registros
        _LOG.exception("no se pudo sincronizar el audio de la sala %s", sala_id)
