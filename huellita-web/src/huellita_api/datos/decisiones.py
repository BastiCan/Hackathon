"""Decisiones de la tía sobre las sugerencias: la regla 7 del spec oficial.

La tabla Decisiones guarda **solo** lo que la tía decidió (`sala_key` + `id_sugerencia`):
una sugerencia sin fila queda `pendiente`, y una decisión `pendiente` borra la fila que
había. `guardar` es un `PutItem` sin condición y `borrar` un `DeleteItem`, así que repetir
la misma llamada deja la misma fila y responde lo mismo: la idempotencia sale de ahí.

`decidir` y `aplicar` son puras: no tocan AWS y las reutiliza `datos/lectura.py`.
"""
from __future__ import annotations

from .. import mapeo
from ..config import Config
from ..modelos import ItemDecision, Original, Sugerencia
from . import dynamo

#: Los únicos estados que se escriben. `pendiente` no se guarda: se borra.
ESTADOS_GUARDABLES: tuple[str, ...] = ("aceptada", "cambiada", "descartada")

#: Una sugerencia de la app es `{id_captura}-p{parte}-{n}` (spec oficial, regla 7).
PREFIJO_CAPTURA = "CAP-"
SEPARADOR_PARTE = "-p"


def _clave(sala_key: str, id_sugerencia: str) -> dict:
    return {"sala_key": {"S": sala_key}, "id_sugerencia": {"S": id_sugerencia}}


def _mapa_original(original: Original) -> dict:
    """El `original` de la IA, como mapa de DynamoDB con los nombres de la tabla."""
    mapa: dict[str, dict] = {}
    if original.ninoId is not None:
        mapa["nino_id"] = {"S": original.ninoId}
    if original.nucleo is not None:
        mapa["nucleo"] = {"S": original.nucleo}
    if original.nivel is not None:
        mapa["nivel"] = {"N": str(original.nivel)}
    return mapa


def _original_de(decision: dict) -> Original | None:
    """El `original` de la IA: el mapa del spec oficial o los `orig_*` de CONTRATOS.md.

    Se escribe siempre como mapa (manda el spec); al leer se aceptan los dos nombres.
    """
    mapa = decision.get("original")
    if not isinstance(mapa, dict):
        mapa = {
            "nino_id": decision.get("orig_nino_id"),
            "nucleo": decision.get("orig_nucleo"),
            "nivel": decision.get("orig_nivel"),
        }
        if all(valor is None for valor in mapa.values()):
            return None
    return Original(ninoId=mapa.get("nino_id"), nucleo=mapa.get("nucleo"), nivel=mapa.get("nivel"))


def guardar(
    cfg: Config,
    sala_key: str,
    id_sugerencia: str,
    *,
    estado: str,
    usuaria_id: str,
    validada_en: str,
    nino_id: str | None = None,
    nucleo: str | None = None,
    nivel: int | None = None,
    original: Original | None = None,
) -> None:
    """Pisa la fila de la decisión. `usuaria_id` se guarda como `validada_por`."""
    if estado not in ESTADOS_GUARDABLES:
        raise ValueError(f"estado que no se guarda: {estado}")
    item = _clave(sala_key, id_sugerencia) | {
        "estado": {"S": estado},
        "validada_por": {"S": usuaria_id},
        "validada_en": {"S": validada_en},
    }
    if nino_id is not None:
        item["nino_id"] = {"S": nino_id}
    if nucleo is not None:
        item["nucleo"] = {"S": nucleo}
    if nivel is not None:
        item["nivel"] = {"N": str(nivel)}
    if original is not None:
        item["original"] = {"M": _mapa_original(original)}
    dynamo.poner(cfg.tabla_decisiones, item)


def borrar(cfg: Config, sala_key: str, id_sugerencia: str) -> None:
    """Deja la sugerencia en `pendiente`: sin fila, no hay decisión."""
    dynamo.borrar(cfg.tabla_decisiones, _clave(sala_key, id_sugerencia))


def leer_por_sala(cfg: Config, sala_key: str) -> dict[str, dict]:
    """Las decisiones de una sala, desanidadas y por `id_sugerencia`."""
    items = dynamo.consultar_todo(
        cfg.tabla_decisiones,
        KeyConditionExpression="sala_key = :sk",
        ExpressionAttributeValues={":sk": {"S": sala_key}},
    )
    decisiones: dict[str, dict] = {}
    for item in items:
        fila = {nombre: mapeo.desanidar(valor) for nombre, valor in item.items()}
        id_sugerencia = fila.get("id_sugerencia")
        if isinstance(id_sugerencia, str):
            decisiones[id_sugerencia] = fila
    return decisiones


def id_captura_de(id_sugerencia: str) -> str | None:
    """`id_obs[:rindex("-p")]`, o `None` si el id no es de una captura de la app."""
    if not id_sugerencia.startswith(PREFIJO_CAPTURA) or SEPARADOR_PARTE not in id_sugerencia:
        return None
    return id_sugerencia[: id_sugerencia.rindex(SEPARADOR_PARTE)]


def leer_sugerencia(cfg: Config, id_sugerencia: str) -> Sugerencia | None:
    """La sugerencia como la dejó la IA en Observaciones, sin decisiones encima.

    Es contra ella que se comparan los cambios de la tía (regla 7), así que repetir la
    misma corrección vuelve a dar `cambiada` con el mismo `original`. Devuelve `None` si
    el id no es de la app (los del dataset, por ejemplo) o si la observación no está.
    """
    id_captura = id_captura_de(id_sugerencia)
    if id_captura is None:
        return None
    item = dynamo.obtener(
        cfg.tabla_observaciones,
        {"id_captura": {"S": id_captura}, "id_obs": {"S": id_sugerencia}},
    )
    if item is None or item.get("origen", {}).get("S") != "app":
        return None
    return mapeo.a_sugerencia(item)


def decidir(sugerencia: Sugerencia, item: ItemDecision) -> tuple[str, Original | None]:
    """Regla 7: el estado que se guarda y el `original` cuando la tía corrigió a la IA.

    Las cinco transiciones: `aceptada` sin cambios y `aceptada` con cambios iguales a los
    de la IA quedan `aceptada` sin `original`; con cambios distintos queda `cambiada` y el
    `original` son los valores de la IA; `descartada` queda `descartada`; `pendiente`
    devuelve `pendiente` y quien llama borra la fila.
    """
    if item.estado == "pendiente":
        return "pendiente", None
    if item.estado == "descartada":
        return "descartada", None
    de_la_ia = sugerencia.original or Original(
        ninoId=sugerencia.ninoId, nucleo=sugerencia.nucleo, nivel=sugerencia.nivel
    )
    if item.cambios is None:
        return "aceptada", None
    if (item.cambios.ninoId, item.cambios.nucleo, item.cambios.nivel) == (
        de_la_ia.ninoId,
        de_la_ia.nucleo,
        de_la_ia.nivel,
    ):
        return "aceptada", None
    return "cambiada", de_la_ia


def aplicar(sugerencia: Sugerencia, decision: dict) -> Sugerencia:
    """La sugerencia con la decisión guardada encima: estado, quién y cuándo, y valores.

    Los valores corregidos solo pisan a los de la IA cuando la fila los trae, para no
    borrar el `ninoId` que la regla 5 acaba de poner. Una fila sin estado válido se ignora.
    """
    estado = decision.get("estado")
    if estado not in ESTADOS_GUARDABLES:
        return sugerencia
    cambios: dict[str, object] = {
        "estado": estado,
        "validadaPor": decision.get("validada_por"),
        "validadaEn": decision.get("validada_en"),
        "original": _original_de(decision),
    }
    for campo, atributo in (("ninoId", "nino_id"), ("nucleo", "nucleo"), ("nivel", "nivel")):
        valor = decision.get(atributo)
        if valor is not None:
            cambios[campo] = valor
    return sugerencia.model_copy(update=cambios)
