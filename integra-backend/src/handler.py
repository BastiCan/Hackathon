"""Lambda handler: evento S3 (capturas) o evento directo -> pipeline -> respuesta.

Dos caminos (design.md "Flujo del handler"):
- **Disparo S3**: el bucket de capturas notifica `meta.json` y `texto.json`.
  - `meta.json`  -> upsert Registros a RECIBIDO (contexto de la captura).
  - `texto.json` -> Registros a PROCESANDO; se lee meta.json + texto.json y se procesa
    cada parte con `procesar_nota`; al terminar: PROCESADO (con `errores[]` por parte),
    SIN_TEXTO (sin partes) o ERROR (si falla todo o es error de captura completa).
- **Invocacion directa**: evento JSON `{texto,id_educadora,sala_grupo,fecha}` (o envuelto
  en `{"body": "<json>"}`); si no trae `id_captura`, se genera. Util para `sam remote invoke`.

Delgado (structure.md): los recursos pesados (rubrica, embeddings, fewshot) se cargan una
vez por contenedor. No se escribe el texto de las notas en logs (requirements 5).
"""

from __future__ import annotations

import json
import logging
import urllib.parse
from datetime import date
from typing import Any

from core import capturas as capturas_mod
from core.config import config
from core.datos import crear_datos
from core.datos_aws import ahora_iso, sala_key
from core.modelos import Entrada, ErrorCaptura, EstadoRegistro, Meta, TextoCaptura
from core.pipeline import ErrorCapturaExc, procesar_nota
from core.recursos import cargar_json, leer_json_s3
from core.retriever import Retriever
from core.rubrica import Rubrica

logging.basicConfig(level=getattr(logging, config.log_level, logging.INFO))
log = logging.getLogger("procesar_nota")

# --- Recursos cacheados por contenedor (se cargan una vez) ---
_rubrica: Rubrica | None = None
_retriever: Retriever | None = None
_fewshot: dict | None = None


def _recursos() -> tuple[Rubrica, Retriever, dict]:
    global _rubrica, _retriever, _fewshot
    if _rubrica is None:
        _rubrica = Rubrica.desde_dict(cargar_json("rubrica"))
        _retriever = Retriever.desde_dict(_rubrica, cargar_json("embeddings"))
        _fewshot = cargar_json("fewshot")
    assert _retriever is not None and _fewshot is not None
    return _rubrica, _retriever, _fewshot


def _error(codigo: str) -> dict[str, Any]:
    return {"error": {"codigo": codigo}}


# --- Deteccion de tipo de evento ---

def _es_evento_s3(event: dict[str, Any]) -> bool:
    registros = event.get("Records") if isinstance(event, dict) else None
    return bool(registros) and isinstance(registros, list) and "s3" in registros[0]


def _clave_del_record(record: dict[str, Any]) -> tuple[str, str]:
    """Devuelve (bucket, key) de un record S3, decodificando el %20 de la key."""
    s3 = record["s3"]
    bucket = s3["bucket"]["name"]
    key = urllib.parse.unquote_plus(s3["object"]["key"])
    return bucket, key


# ============================ Camino S3 ============================

def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    if _es_evento_s3(event):
        return _manejar_s3(event)
    return _manejar_directo(event)


def _manejar_s3(event: dict[str, Any]) -> dict[str, Any]:
    datos = crear_datos()
    resultados: list[dict[str, Any]] = []
    for record in event["Records"]:
        if "s3" not in record:
            continue
        bucket, key = _clave_del_record(record)
        try:
            id_captura = capturas_mod.id_captura_de_clave(key)
        except capturas_mod.ClaveInvalida:
            log.warning("record S3 con clave invalida, se ignora")
            continue
        tipo = capturas_mod.tipo_de_clave(key)
        if tipo == "meta":
            resultados.append(_procesar_meta(datos, bucket, id_captura, key))
        elif tipo == "texto":
            resultados.append(_procesar_texto(datos, bucket, id_captura, key))
        else:
            log.info("objeto S3 ignorado (no es meta/texto)")
    return {"procesados": resultados}


def _procesar_meta(datos: Any, bucket: str, id_captura: str, key: str) -> dict[str, Any]:
    """meta.json -> upsert Registros a RECIBIDO con el contexto de la captura."""
    try:
        meta = Meta.model_validate(leer_json_s3(bucket, key))
    except Exception as e:  # noqa: BLE001 - meta ausente/invalido
        log.warning("meta.json invalido para %s: %s", id_captura, type(e).__name__)
        # El aviso de meta.json no debe pisar un estado mas avanzado (carrera S3).
        datos.upsert_registro(
            id_captura,
            {
                "estado": EstadoRegistro.ERROR.value,
                "error": ErrorCaptura.META_INVALIDA.value,
                "clave_meta": key,
            },
            conservar_si_existe={"estado"},
        )
        return {"id_captura": id_captura, "estado": EstadoRegistro.ERROR.value}

    # estado/subido_en con if_not_exists: si texto.json llego antes, no retrocede el estado.
    datos.upsert_registro(
        id_captura,
        {
            "estado": EstadoRegistro.RECIBIDO.value,
            "id_educadora": meta.id_educadora,
            "sala_grupo": meta.sala_grupo,
            "sala_key": _sala_key_de_meta(datos, meta),
            "fecha_observacion": meta.fecha_observacion.isoformat(),
            "tipo": meta.tipo,
            "clave_meta": key,
            "subido_en": ahora_iso(),
        },
        conservar_si_existe={"estado", "subido_en"},
    )
    log.info("captura %s recibida (meta.json)", id_captura)
    return {"id_captura": id_captura, "estado": EstadoRegistro.RECIBIDO.value}


def _procesar_texto(datos: Any, bucket: str, id_captura: str, key: str) -> dict[str, Any]:
    """texto.json -> PROCESANDO -> procesar cada parte -> PROCESADO/SIN_TEXTO/ERROR."""
    datos.upsert_registro(id_captura, {"estado": EstadoRegistro.PROCESANDO.value, "clave_texto": key})

    # Contexto obligatorio: meta.json. Si falta o es invalido -> ERROR de captura completa.
    try:
        meta = Meta.model_validate(leer_json_s3(bucket, _clave_meta(id_captura)))
    except Exception as e:  # noqa: BLE001
        log.warning("texto.json sin meta.json valido para %s: %s", id_captura, type(e).__name__)
        datos.upsert_registro(
            id_captura,
            {
                "estado": EstadoRegistro.ERROR.value,
                "error": ErrorCaptura.META_INVALIDA.value,
                "procesado_en": ahora_iso(),
            },
        )
        return {"id_captura": id_captura, "estado": EstadoRegistro.ERROR.value}

    try:
        texto = TextoCaptura.model_validate(leer_json_s3(bucket, key))
    except Exception as e:  # noqa: BLE001 - texto.json invalido
        log.warning("texto.json invalido para %s: %s", id_captura, type(e).__name__)
        datos.upsert_registro(
            id_captura,
            {
                "estado": EstadoRegistro.ERROR.value,
                "error": ErrorCaptura.TEXTO_INVALIDO.value,
                "procesado_en": ahora_iso(),
            },
        )
        return {"id_captura": id_captura, "estado": EstadoRegistro.ERROR.value}

    partes = texto.partes_normalizadas()
    if not partes:
        datos.upsert_registro(
            id_captura,
            {"estado": EstadoRegistro.SIN_TEXTO.value, "procesado_en": ahora_iso()},
        )
        log.info("captura %s sin texto", id_captura)
        return {"id_captura": id_captura, "estado": EstadoRegistro.SIN_TEXTO.value}

    rubrica, retriever, fewshot = _recursos()
    errores: list[dict[str, Any]] = []
    total_obs = 0
    error_captura_completa: str | None = None

    for n_parte, parte in enumerate(partes):
        archivo_s3 = (
            capturas_mod.clave_archivo(id_captura, parte.archivo) if parte.archivo else None
        )
        try:
            entrada = Entrada(
                texto=parte.texto,
                id_educadora=meta.id_educadora,
                sala_grupo=meta.sala_grupo,
                fecha=meta.fecha_observacion,
            )
            resultado = procesar_nota(
                entrada,
                datos,
                rubrica,
                retriever,
                fewshot,
                id_captura=id_captura,
                n_parte=n_parte,
                archivo_s3=archivo_s3,
            )
            total_obs += len(resultado.observaciones)
        except ErrorCapturaExc as e:
            # EDUCADORA/SALA_DESCONOCIDA afectan a toda la captura (vienen de meta).
            if e.codigo in (ErrorCaptura.EDUCADORA_DESCONOCIDA, ErrorCaptura.SALA_DESCONOCIDA):
                error_captura_completa = e.codigo.value
                break
            errores.append({"n_parte": n_parte, "error": e.codigo.value})
        except Exception as e:
            log.exception("fallo la parte %d de %s (%s)", n_parte, id_captura, type(e).__name__)
            errores.append({"n_parte": n_parte, "error": "ERROR_INTERNO"})

    if error_captura_completa is not None:
        datos.upsert_registro(
            id_captura,
            {
                "estado": EstadoRegistro.ERROR.value,
                "error": error_captura_completa,
                "procesado_en": ahora_iso(),
            },
        )
        return {"id_captura": id_captura, "estado": EstadoRegistro.ERROR.value}

    # Si TODAS las partes fallaron -> ERROR; si no, PROCESADO con la lista de errores.
    if errores and len(errores) == len(partes):
        datos.upsert_registro(
            id_captura,
            {
                "estado": EstadoRegistro.ERROR.value,
                "errores": errores,
                "procesado_en": ahora_iso(),
            },
        )
        log.info("captura %s con error en todas las partes", id_captura)
        return {"id_captura": id_captura, "estado": EstadoRegistro.ERROR.value}

    datos.upsert_registro(
        id_captura,
        {
            "estado": EstadoRegistro.PROCESADO.value,
            "errores": errores,
            "procesado_en": ahora_iso(),
        },
    )
    log.info("captura %s procesada: %d observaciones, %d errores", id_captura, total_obs, len(errores))
    return {
        "id_captura": id_captura,
        "estado": EstadoRegistro.PROCESADO.value,
        "observaciones": total_obs,
        "errores": errores,
    }


def _clave_meta(id_captura: str) -> str:
    return capturas_mod.clave_archivo(id_captura, "meta.json")


def _sala_key_de_meta(datos: Any, meta: Meta) -> str | None:
    """sala_key = '{id_jardin}#{sala_grupo}'; id_jardin se resuelve via la educadora."""
    educadora = datos.educadora(meta.id_educadora)
    if educadora is None:
        return None
    return sala_key(educadora.id_jardin, meta.sala_grupo)


# ========================= Camino directo =========================

def _parsear_evento_directo(event: dict[str, Any]) -> dict[str, Any]:
    """Acepta el evento directo o envuelto en {'body': '<json>'} (estilo API Gateway)."""
    if isinstance(event, dict) and "body" in event and isinstance(event["body"], str):
        return json.loads(event["body"])
    return event


def _manejar_directo(event: dict[str, Any]) -> dict[str, Any]:
    try:
        datos_evento = _parsear_evento_directo(event)
        entrada = Entrada(
            texto=datos_evento.get("texto", ""),
            id_educadora=datos_evento.get("id_educadora", ""),
            sala_grupo=datos_evento.get("sala_grupo", ""),
            fecha=date.fromisoformat(datos_evento["fecha"]),
        )
        id_captura = datos_evento.get("id_captura")  # opcional; si falta, lo genera el pipeline
    except Exception as e:  # noqa: BLE001 - evento mal formado
        log.warning("evento invalido: %s", type(e).__name__)
        return _error("ENTRADA_INVALIDA")

    rubrica, retriever, fewshot = _recursos()
    datos = crear_datos()

    try:
        resultado = procesar_nota(
            entrada, datos, rubrica, retriever, fewshot, id_captura=id_captura
        )
    except ErrorCapturaExc as e:
        log.info("error de captura: %s", e.codigo.value)
        return _error(e.codigo.value)
    except Exception as e:
        log.exception("error interno procesando captura (%s)", type(e).__name__)
        return {"error": {"codigo": "ERROR_INTERNO"}}

    log.info(
        "captura %s procesada: %d observaciones",
        resultado.id_captura,
        len(resultado.observaciones),
    )
    return json.loads(resultado.model_dump_json(exclude_none=True))
