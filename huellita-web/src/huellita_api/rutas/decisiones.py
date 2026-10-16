"""`PUT /api/decisiones`: la tía confirma, corrige, descarta o vuelve a dejar pendiente.

Sigue la regla 7 del spec oficial: valida la solicitud completa **antes** de escribir,
compara los cambios contra la sugerencia leída de Observaciones, guarda o borra la
decisión y responde con todas las sugerencias de la sala ya actualizadas. Repetir la misma
llamada da el mismo resultado, salvo `validadaEn`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Header

from .. import auth, errores, tiempo
from ..config import Config, cargar_config
from ..datos import decisiones as datos_decisiones
from ..datos import lectura
from ..modelos import DecisionesEntrada, ItemDecision, Original, Sugerencia, SugerenciasActualizadas
from . import PREFIJO

router = APIRouter(prefix=PREFIJO, tags=["decisiones"])

_cfg: Config | None = None


def configurar(cfg: Config) -> None:
    """Fija el `Config` del proceso; lo llama `app.py` al arrancar."""
    global _cfg
    _cfg = cfg


def config_actual() -> Config:
    """El `Config` fijado por `app.py`; si nadie lo fijó, se lee del entorno una vez."""
    global _cfg
    if _cfg is None:
        _cfg = cargar_config()
    return _cfg


@dataclass(frozen=True)
class _Plan:
    """Un ítem ya validado y decidido, listo para escribirse."""

    id_sugerencia: str
    de_la_ia: Sugerencia
    estado: str
    original: Original | None
    nino_id: str | None
    nucleo: str | None
    nivel: int | None


def _planificar(cfg: Config, sala_id: str, item: ItemDecision, ninos: set[str] | None) -> _Plan:
    de_la_ia = datos_decisiones.leer_sugerencia(cfg, item.idSugerencia)
    if de_la_ia is None or de_la_ia.salaId != sala_id:
        raise errores.error("sugerencia_desconocida")  # 404: no es una sugerencia de la app de esa sala
    if item.cambios is not None and (ninos is None or item.cambios.ninoId not in ninos):
        raise errores.error("nino_de_otra_sala")
    estado, original = datos_decisiones.decidir(de_la_ia, item)
    valores = item.cambios or de_la_ia
    return _Plan(
        id_sugerencia=item.idSugerencia,
        de_la_ia=de_la_ia,
        estado=estado,
        original=original,
        nino_id=valores.ninoId,
        nucleo=valores.nucleo,
        nivel=valores.nivel,
    )


def _decision_de(plan: _Plan, usuaria_id: str, validada_en: str) -> dict:
    """La fila que queda guardada, en la forma que espera `decisiones.aplicar`."""
    decision: dict = {
        "estado": plan.estado,
        "validada_por": usuaria_id,
        "validada_en": validada_en,
        "nino_id": plan.nino_id,
        "nucleo": plan.nucleo,
        "nivel": plan.nivel,
    }
    if plan.original is not None:
        decision["original"] = {
            "nino_id": plan.original.ninoId,
            "nucleo": plan.original.nucleo,
            "nivel": plan.original.nivel,
        }
    return decision


def _con_decision(base: Sugerencia, plan: _Plan, usuaria_id: str, validada_en: str) -> Sugerencia:
    if plan.estado == "pendiente":
        de_la_ia = base.original or Original(ninoId=base.ninoId, nucleo=base.nucleo, nivel=base.nivel)
        return base.model_copy(
            update={
                "estado": "pendiente",
                "validadaPor": None,
                "validadaEn": None,
                "original": None,
                "ninoId": de_la_ia.ninoId,
                "nucleo": de_la_ia.nucleo,
                "nivel": de_la_ia.nivel,
            }
        )
    return datos_decisiones.aplicar(base, _decision_de(plan, usuaria_id, validada_en))


def _sugerencias_de_la_sala(
    cfg: Config, sala_id: str, planes: list[_Plan], usuaria_id: str, validada_en: str
) -> list[Sugerencia]:
    """Las sugerencias de la sala con lo recién decidido encima.

    La consulta a DynamoDB es eventualmente consistente, así que lo de esta llamada se
    vuelve a aplicar sobre lo leído en vez de confiar en que ya se vea.
    """
    sugerencias = {s.id: s for s in lectura.leer_registros(cfg, sala_id).sugerencias}
    for plan in planes:
        base = sugerencias.get(plan.id_sugerencia, plan.de_la_ia)
        sugerencias[plan.id_sugerencia] = _con_decision(base, plan, usuaria_id, validada_en)
    return sorted(sugerencias.values(), key=lambda s: (s.evidenciaId, s.id))


@router.put("/decisiones", response_model=SugerenciasActualizadas, response_model_exclude_none=True)
def guardar_decisiones(
    entrada: DecisionesEntrada,
    id_usuaria: Annotated[str | None, Header(alias=auth.CABECERA_USUARIA)] = None,
) -> SugerenciasActualizadas:
    cfg = config_actual()
    usuaria = auth.usuaria_o_error(id_usuaria)
    auth.exigir_sala(cfg, usuaria, entrada.salaId)
    if entrada.usuariaId != usuaria.id:
        raise errores.error("sin_acceso")

    ninos: set[str] | None = None
    if any(item.cambios is not None for item in entrada.items):
        ninos = {nino.id for nino in lectura.leer_ninos(cfg, entrada.salaId)}
    planes = [_planificar(cfg, entrada.salaId, item, ninos) for item in entrada.items]

    sala_key = cfg.sala_key(entrada.salaId)
    validada_en = tiempo.iso(tiempo.ahora(cfg))
    for plan in planes:
        if plan.estado == "pendiente":
            datos_decisiones.borrar(cfg, sala_key, plan.id_sugerencia)
        else:
            datos_decisiones.guardar(
                cfg,
                sala_key,
                plan.id_sugerencia,
                estado=plan.estado,
                usuaria_id=entrada.usuariaId,
                validada_en=validada_en,
                nino_id=plan.nino_id,
                nucleo=plan.nucleo,
                nivel=plan.nivel,
                original=plan.original,
            )
    return SugerenciasActualizadas(
        sugerencias=_sugerencias_de_la_sala(cfg, entrada.salaId, planes, entrada.usuariaId, validada_en)
    )
