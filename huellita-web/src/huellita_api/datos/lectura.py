"""Lo que ve la tía al abrir Huellita: el contexto, los niños de su sala y sus registros.

`leer_registros` junta cuatro fuentes en una sola respuesta: las capturas propias de la
tabla Capturas, lo que dice Registros de integra-procesador, el historial del dataset
(regla 4) y las observaciones nuevas de la IA (regla 5), con las decisiones de la tía
encima (regla 7).

Acá no se habla con el transcriptor: las transcripciones las pone al día
`datos/audio.sincronizar`, que `rutas/lectura.py` llama **antes** de leer (CONTRATOS.md §2),
así este módulo solo lee DynamoDB.
"""
from __future__ import annotations

import logging
from datetime import datetime

from .. import auth, errores, mapeo, tiempo
from ..config import Config
from ..modelos import Contexto, EstadoEvidencia, Evidencia, Nino, Registros, Sugerencia
from . import decisiones, dynamo

_log = logging.getLogger(__name__)


def leer_contexto(cfg: Config, reloj: tiempo.Reloj | None = None) -> Contexto:
    """El jardín, sus salas de la demo y las tías. Regla 1 para el nivel de cada sala."""
    item = dynamo.obtener(cfg.tabla_jardines, {"id_jardin": {"S": cfg.jardin}})
    if item is None:
        raise errores.error("no_encontrado")
    ninos = mapeo.a_ninos(_items_de_ninos(cfg))
    hoy = tiempo.dia(tiempo.reloj_de(cfg, reloj))
    return Contexto(
        jardin=mapeo.a_jardin(item),
        salas=mapeo.a_salas(item, cfg, ninos, hoy),
        usuarias=auth.usuarias(),
    )


def leer_ninos(cfg: Config, sala_id: str) -> list[Nino]:
    """Los niños de una sala, por nombre (regla 2)."""
    items = [item for item in _items_de_ninos(cfg) if _cadena(item, "sala_grupo") == sala_id]
    return mapeo.a_ninos(items)


def leer_nino(cfg: Config, id_nino: str) -> Nino:
    """Un niño o niña del jardín de la demo; `no_encontrado` si no está (regla 2)."""
    item = dynamo.obtener(
        cfg.tabla_ninos,
        {"id_jardin": {"S": cfg.jardin}, "id_nino": {"S": id_nino}},
    )
    if item is None or not _cadena(item, "nombre"):
        raise errores.error("no_encontrado")
    return mapeo.a_nino(item)


def leer_registros(cfg: Config, sala_id: str, reloj: tiempo.Reloj | None = None) -> Registros:
    """Las evidencias y las sugerencias de una sala, en el orden que espera Huellita.

    Las evidencias quedan ordenadas por `creadaEn` ascendente (la última capturada al
    final) y las sugerencias por `(evidenciaId, id)`.
    """
    momento = tiempo.reloj_de(cfg, reloj)
    sala_key = cfg.sala_key(sala_id)

    filas = _filas_propias(cfg, sala_key)
    registros = _registros_pendientes(cfg, filas)

    observaciones = _observaciones(cfg, sala_key)
    de_la_app = [item for item in observaciones if _cadena(item, "origen") == "app"]
    del_historial = [item for item in observaciones if _cadena(item, "origen") != "app"]
    textos = _texto_por_captura(de_la_app)

    evidencias = _evidencias_propias(cfg, filas, registros, textos, momento)
    for item in _items_de_registros(cfg, sala_key):
        id_captura = _cadena(item, "id_captura")
        if id_captura and id_captura not in evidencias:
            evidencias[id_captura] = mapeo.a_evidencia_registro(item, _estado_ajeno(cfg, item, momento))
    for item in de_la_app:
        id_captura = _cadena(item, "id_captura")
        if id_captura and id_captura not in evidencias:
            evidencias[id_captura] = mapeo.a_evidencia_observacion(item)
    for item in del_historial:
        evidencia = mapeo.a_evidencia_historial(item)
        evidencias[evidencia.id] = evidencia
    _rellenar_textos(evidencias, textos)

    sugeridos = _nino_sugerido_por_captura(filas)
    sugerencias = [_regla5(mapeo.a_sugerencia(item), sugeridos) for item in de_la_app]
    for item in del_historial:
        sugerencias.extend(mapeo.a_sugerencias_historial(item))
    sugerencias = _aplicar_decisiones(cfg, sala_key, sugerencias)

    return Registros(
        evidencias=sorted(evidencias.values(), key=lambda e: e.creadaEn),
        sugerencias=sorted(sugerencias, key=lambda s: (s.evidenciaId, s.id)),
    )


# --- lecturas sueltas ------------------------------------------------------------------


def _cadena(item: dict, clave: str) -> str:
    """El atributo de un ítem crudo como texto ("" si falta)."""
    valor = mapeo.desanidar(item.get(clave, {}))
    return valor if isinstance(valor, str) else ""


def _items_de_ninos(cfg: Config) -> list[dict]:
    return dynamo.consultar_todo(
        cfg.tabla_ninos,
        KeyConditionExpression="id_jardin = :j",
        ExpressionAttributeValues={":j": {"S": cfg.jardin}},
    )


def _por_sala(cfg: Config, tabla: str, sala_key: str) -> list[dict]:
    """`Query` al índice `porSala` de una tabla por `sala_key`."""
    return dynamo.consultar_todo(
        tabla,
        IndexName="porSala",
        KeyConditionExpression="sala_key = :sk",
        ExpressionAttributeValues={":sk": {"S": sala_key}},
    )


def _filas_propias(cfg: Config, sala_key: str) -> list[dict]:
    """Las filas de Capturas de la sala. El contador diario no tiene `creada_en`."""
    filas = _por_sala(cfg, cfg.tabla_capturas, sala_key)
    return [fila for fila in filas if _cadena(fila, "creada_en")]


def _items_de_registros(cfg: Config, sala_key: str) -> list[dict]:
    return _por_sala(cfg, cfg.tabla_registros, sala_key)


def _observaciones(cfg: Config, sala_key: str) -> list[dict]:
    return _por_sala(cfg, cfg.tabla_observaciones, sala_key)


def _registros_pendientes(cfg: Config, filas: list[dict]) -> dict[str, dict]:
    """Registros de las capturas que todavía no tienen estado final; de las demás, nada."""
    claves = [
        {"id_captura": {"S": _cadena(fila, "id_captura")}}
        for fila in filas
        if not _cadena(fila, "estado_final")
    ]
    return dynamo.obtener_varios(cfg.tabla_registros, claves)


# --- evidencias ------------------------------------------------------------------------


def _evidencias_propias(
    cfg: Config,
    filas: list[dict],
    registros: dict[str, dict],
    textos: dict[str, str],
    momento: datetime,
) -> dict[str, Evidencia]:
    """Las capturas de la tabla propia, con el estado de la regla 6 ya resuelto."""
    evidencias: dict[str, Evidencia] = {}
    for fila in filas:
        id_captura = _cadena(fila, "id_captura")
        registro = registros.get(id_captura)
        estado = mapeo.regla6(fila, registro, momento, cfg.minutos_max_procesando)
        evidencia = mapeo.a_evidencia_captura(fila, estado)
        relleno = None
        if not evidencia.textoExtraido and textos.get(id_captura):
            relleno = textos[id_captura]
            evidencia = evidencia.model_copy(update={"textoExtraido": relleno})
        evidencias[id_captura] = evidencia
        final = _cierre_desde_registros(fila, registro)
        if final is not None:
            _cerrar_fila(cfg, id_captura, final, relleno, momento)
    return evidencias


def _estado_ajeno(cfg: Config, item: dict, momento: datetime) -> EstadoEvidencia:
    """Estado de una evidencia que solo existe en Registros, con el vencimiento aparte."""
    estado = mapeo.estado_de_registro(_cadena(item, "estado"))
    if estado == "procesando":
        if tiempo.minutos_desde(_cadena(item, "subido_en"), momento) > cfg.minutos_max_procesando:
            return "error"
    return estado


def _cierre_desde_registros(fila: dict, registro: dict | None) -> str | None:
    """El estado final que hay que guardar, cuando lo decidió Registros.

    Un `error` por vencimiento no se guarda: si el resultado llega tarde, todavía gana.
    """
    if _cadena(fila, "estado_final") or mapeo.desanidar(fila.get("archivada", {})) is True:
        return None
    if _cadena(fila, "estado_envio") != "enviada" or registro is None:
        return None
    estado = mapeo.estado_de_registro(_cadena(registro, "estado"))
    return estado if estado in mapeo.ESTADOS_FINALES else None


def _cerrar_fila(
    cfg: Config,
    id_captura: str,
    estado_final: str,
    texto_extraido: str | None,
    momento: datetime,
) -> None:
    """Guarda el estado final en la fila para no volver a preguntarle a Registros."""
    asignaciones = ["estado_final = :f", "actualizado_en = :a"]
    valores: dict = {":f": {"S": estado_final}, ":a": {"S": tiempo.iso(momento)}}
    if texto_extraido:
        asignaciones.append("texto_extraido = :t")
        valores[":t"] = {"S": texto_extraido}
    try:
        dynamo.actualizar(
            cfg.tabla_capturas,
            {"id_captura": {"S": id_captura}},
            "SET " + ", ".join(asignaciones),
            valores,
        )
    except Exception:  # noqa: BLE001 - guardar el estado es de más: la respuesta sigue igual
        _log.warning("no se pudo guardar el estado final de %s", id_captura, exc_info=True)


def _texto_por_captura(observaciones: list[dict]) -> dict[str, str]:
    """El `texto_literal` de la primera observación de cada captura."""
    textos: dict[str, str] = {}
    for item in observaciones:
        id_captura = _cadena(item, "id_captura")
        texto = _cadena(item, "texto_literal")
        if id_captura and texto and id_captura not in textos:
            textos[id_captura] = texto
    return textos


def _rellenar_textos(evidencias: dict[str, Evidencia], textos: dict[str, str]) -> None:
    """Una evidencia sin texto se queda con el de su observación."""
    for id_evidencia, evidencia in evidencias.items():
        texto = textos.get(id_evidencia)
        if texto and not evidencia.textoExtraido:
            evidencias[id_evidencia] = evidencia.model_copy(update={"textoExtraido": texto})


# --- sugerencias -----------------------------------------------------------------------


def _nino_sugerido_por_captura(filas: list[dict]) -> dict[str, str]:
    return {
        _cadena(fila, "id_captura"): _cadena(fila, "nino_id_sugerido")
        for fila in filas
        if _cadena(fila, "nino_id_sugerido")
    }


def _regla5(sugerencia: Sugerencia, sugeridos: dict[str, str]) -> Sugerencia:
    """Regla 5: la nota tomada desde la ficha ya sabe de quién es."""
    if sugerencia.ninoId:
        return sugerencia
    nino_id = sugeridos.get(sugerencia.evidenciaId)
    return sugerencia.model_copy(update={"ninoId": nino_id}) if nino_id else sugerencia


def _aplicar_decisiones(cfg: Config, sala_key: str, sugerencias: list[Sugerencia]) -> list[Sugerencia]:
    """Regla 7: lo que la tía confirmó, corrigió o descartó manda sobre la IA."""
    guardadas = decisiones.leer_por_sala(cfg, sala_key)
    if not guardadas:
        return sugerencias
    return [
        decisiones.aplicar(sugerencia, guardadas[sugerencia.id]) if sugerencia.id in guardadas else sugerencia
        for sugerencia in sugerencias
    ]
