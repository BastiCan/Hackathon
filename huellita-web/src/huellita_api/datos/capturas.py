"""Filas de la tabla Capturas y contador atómico del tope diario.

SPEC-OFICIAL.md §2 manda sobre CONTRATOS.md §5: la clave es `id_captura`, el
índice `porSala` es `sala_key` + `creada_en`, la sala de la fila va en
`sala_grupo` (no `sala_id`) y el contador del día es el ítem
`CONTADOR#AAAA-MM-DD` con el atributo `total`, sin `sala_key` para que quede
fuera del índice.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .. import errores, tiempo
from . import dynamo

if TYPE_CHECKING:  # pragma: no cover - solo para los tipos
    from ..config import Config

ENVIOS = ("enviando", "enviada", "error_envio")
FINALES = ("lista", "error")
INDICE_SALA = "porSala"
PREFIJO_CONTADOR = "CONTADOR#"


def _clave(id_captura: str) -> dict:
    """Clave de la tabla en formato AttributeValue."""
    return {"id_captura": {"S": id_captura}}


def _ahora(cfg: Config) -> dict:
    """Marca de la escritura, en hora de Chile."""
    return {"S": tiempo.iso(tiempo.ahora(cfg))}


def id_contador(dia: str) -> str:
    """Id del ítem contador del día: `CONTADOR#2026-10-15`."""
    return f"{PREFIJO_CONTADOR}{dia}"


def reservar_cupo_del_dia(cfg: Config, sala_id: str, dia: str) -> int:
    """Suma 1 al contador del día con un solo `UpdateItem` condicional y
    devuelve el total. Si ya se alcanzó `MAX_CAPTURAS_DIA`, lanza `tope_diario`
    (429). El tope es del día completo, así que `sala_id` no entra en la clave.
    """
    del sala_id  # el contador no se parte por sala (SPEC-OFICIAL §2)
    item = dynamo.actualizar(
        cfg.tabla_capturas,
        _clave(id_contador(dia)),
        "ADD #total :uno",
        {":uno": {"N": "1"}, ":max": {"N": str(cfg.max_capturas_dia)}},
        condicion="attribute_not_exists(#total) OR #total < :max",
        nombres={"#total": "total"},
    )
    if item is None:
        raise errores.error("tope_diario")
    return int(item["total"]["N"])


def contar_del_dia(cfg: Config, sala_id: str, dia: str) -> int:
    """Lee el contador del día. Solo para pruebas y prueba de humo."""
    del sala_id  # el contador no se parte por sala (SPEC-OFICIAL §2)
    item = dynamo.obtener(cfg.tabla_capturas, _clave(id_contador(dia)))
    if not item or "total" not in item:
        return 0
    return int(item["total"]["N"])


def crear_fila(
    cfg: Config,
    *,
    id_captura: str,
    sala_id: str,
    autor_id: str,
    formato: str,
    creada_en: str,
    dia: str,
    nino_id_sugerido: str | None = None,
    mime_type: str | None = None,
) -> None:
    """Guarda la fila nueva con `estado_envio = "enviando"`, sin `estado_final`
    y sin `archivada`. La evidencia la arma quien llama."""
    item = {
        "id_captura": {"S": id_captura},
        "sala_key": {"S": cfg.sala_key(sala_id)},
        "creada_en": {"S": creada_en},
        "id_jardin": {"S": cfg.jardin},
        "sala_grupo": {"S": sala_id},
        "autor_id": {"S": autor_id},
        "formato": {"S": formato},
        "dia": {"S": dia},
        "estado_envio": {"S": "enviando"},
        "actualizado_en": {"S": creada_en},
    }
    if nino_id_sugerido:
        item["nino_id_sugerido"] = {"S": nino_id_sugerido}
    if mime_type:
        item["mime_type"] = {"S": mime_type}
    dynamo.poner(cfg.tabla_capturas, item)


def marcar_envio(
    cfg: Config,
    id_captura: str,
    estado_envio: str,
    *,
    id_trabajo: str | None = None,
    texto_entregado: bool | None = None,
) -> None:
    """Deja la fila en `enviando`, `enviada` o `error_envio`. `id_trabajo` es el
    trabajo del transcriptor y `texto_entregado` marca que el `texto.json` del
    audio ya se escribió."""
    if estado_envio not in ENVIOS:
        raise ValueError(f"estado_envio inválido: {estado_envio}")
    partes = ["estado_envio = :e", "actualizado_en = :a"]
    valores: dict = {":e": {"S": estado_envio}, ":a": _ahora(cfg)}
    if id_trabajo is not None:
        partes.append("id_trabajo = :t")
        valores[":t"] = {"S": id_trabajo}
    if texto_entregado is not None:
        partes.append("texto_entregado = :x")
        valores[":x"] = {"BOOL": texto_entregado}
    dynamo.actualizar(cfg.tabla_capturas, _clave(id_captura), "SET " + ", ".join(partes), valores)


def marcar_final(
    cfg: Config,
    id_captura: str,
    estado_final: str,
    *,
    texto_extraido: str | None = None,
) -> None:
    """Cierra la captura en `lista` o `error` para no volver a consultarla."""
    if estado_final not in FINALES:
        raise ValueError(f"estado_final inválido: {estado_final}")
    partes = ["estado_final = :f", "actualizado_en = :a"]
    valores: dict = {":f": {"S": estado_final}, ":a": _ahora(cfg)}
    if texto_extraido is not None:
        partes.append("texto_extraido = :x")
        valores[":x"] = {"S": texto_extraido}
    dynamo.actualizar(cfg.tabla_capturas, _clave(id_captura), "SET " + ", ".join(partes), valores)


def guardar_texto(cfg: Config, id_captura: str, texto: str) -> None:
    """Guarda el texto escrito por la tía o la transcripción del audio."""
    dynamo.actualizar(
        cfg.tabla_capturas,
        _clave(id_captura),
        "SET texto_extraido = :x, actualizado_en = :a",
        {":x": {"S": texto}, ":a": _ahora(cfg)},
    )


def archivar(cfg: Config, id_captura: str, sala_id: str) -> bool:
    """Marca la captura como archivada y la deja `lista`. `False` si no existe o
    es de otra sala."""
    item = dynamo.actualizar(
        cfg.tabla_capturas,
        _clave(id_captura),
        "SET archivada = :si, estado_final = :lista, actualizado_en = :a",
        {
            ":si": {"BOOL": True},
            ":lista": {"S": "lista"},
            ":a": _ahora(cfg),
            ":sk": {"S": cfg.sala_key(sala_id)},
        },
        condicion="attribute_exists(id_captura) AND sala_key = :sk",
    )
    return item is not None


def obtener(cfg: Config, id_captura: str) -> dict | None:
    """Fila de una captura, en formato AttributeValue."""
    return dynamo.obtener(cfg.tabla_capturas, _clave(id_captura))


def leer_de_sala(cfg: Config, sala_id: str) -> list[dict]:
    """Capturas propias de la sala por el índice `porSala`, sin los contadores."""
    items = dynamo.consultar_todo(
        cfg.tabla_capturas,
        IndexName=INDICE_SALA,
        KeyConditionExpression="sala_key = :sk",
        ExpressionAttributeValues={":sk": {"S": cfg.sala_key(sala_id)}},
    )
    return [item for item in items if "creada_en" in item]
