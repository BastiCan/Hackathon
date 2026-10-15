"""Lambda `postits-ocr`: separa los post-its de una foto ya subida al bucket de capturas, los lee con
Bedrock y deja la captura con el contrato que procesa ProcesarNota (integra-backend).

Handler: ocr.handler (python3.12). Invocación directa (boto3 invoke), evento JSON o {"body": "<json>"}:

    {"id_captura": "CAP-01K...",            # o "s3_key": "capturas/..."; ver captura.validar_peticion
     "id_educadora": "EDU-0001",            # obligatorios si la captura no tiene meta.json
     "sala_grupo": "SG-A",
     "fecha_observacion": "2026-10-15",     # opcional; por defecto hoy en America/Santiago
     "modo": "opencv",                      # opencv (por defecto) | llm (fuerza el Plan B)
     "escribir_texto": true,                # false = ensayo en seco: no escribe meta.json ni texto.json
     "incluir_urls": false}                 # true = URLs prefirmadas (1 h) de recortes y overlay

Orden de escritura en capturas/{id}/: original/foto.jpg (si el origen es otra clave), los recortes
original/postit_NN.jpg y original/overlay.jpg; después meta.json solo si no existe (dispara
ProcesarNota: fila RECIBIDO en Registros) y al final texto.json (dispara el procesamiento). Cada
parte de texto.json lleva su `archivo`, que ProcesarNota copia como `archivo_s3` en Observaciones.

Respuesta: {"id_captura", "prefijo", "n_postits", "modo", "giro_grados", "partes": [{"orden", "archivo",
"texto", "legibilidad", "color"}], "no_leidos": [{"orden", "archivo"}], "tiempos_ms", "meta_escrito",
"texto_escrito", "avisos"} (+ "documentos" en el ensayo en seco). Error: {"error": {"codigo", "mensaje"},
"id_captura"?}.

Orientación: el eje de la letra sale de los perfiles de proyección de la tinta (sin el modelo); solo si
está vertical, el modelo elige entre 90° y 270°. Freno: una parte con legibilidad baja va a texto.json
como [ilegible] (ProcesarNota no le asigna niño) y queda en no_leidos, con el aviso LECTURA_BAJA: N.

Los eventos S3 se ignoran ("ignorada") hasta que el equipo agregue el disparador.
Los logs llevan solo IDs, conteos, tiempos y códigos: nunca textos leídos ni nombres.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
from botocore.exceptions import BotoCoreError, ClientError

import almacen as almacen_mod
import captura
import detectar
import leer
import nomina as nomina_mod
import recortar

log = logging.getLogger("postits.ocr")
logging.getLogger("postits").setLevel(os.environ.get("POSTITS_LOG", "INFO").upper())

MAX_ORIGEN = 25 * 1024 * 1024
MARGEN_RESPUESTA_S = 20
TIPO_JSON = "application/json; charset=utf-8"
TIPO_JPEG = "image/jpeg"


def _versiones() -> dict:
    from importlib.metadata import PackageNotFoundError, version

    salida = {"evento": "inicio", "python": sys.version.split()[0]}
    for paquete, campo in (("boto3", "boto3"), ("botocore", "botocore"), ("python-ulid", "python_ulid")):
        try:
            salida[campo] = version(paquete)
        except PackageNotFoundError:
            salida[campo] = None
    return salida


_INICIO = _versiones()


class Fallo(Exception):
    def __init__(self, codigo: str, mensaje: str):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def _json_bytes(doc) -> bytes:
    return json.dumps(doc, ensure_ascii=False, indent=1).encode("utf-8")


def _s3(operacion, *args, **kwargs):
    """Llamada al almacén; los errores de AWS pasan a ERROR_ALMACENAMIENTO (con el código, sin valores)."""
    try:
        return operacion(*args, **kwargs)
    except ClientError as e:
        codigo = e.response.get("Error", {}).get("Code", "ClientError")
        log.error("s3_error op=%s codigo=%s", getattr(operacion, "__name__", "?"), codigo)
        raise Fallo("ERROR_ALMACENAMIENTO", f"S3 fallo ({codigo})") from None
    except BotoCoreError as e:
        log.error("s3_error op=%s tipo=%s", getattr(operacion, "__name__", "?"), type(e).__name__)
        raise Fallo("ERROR_ALMACENAMIENTO", f"S3 fallo ({type(e).__name__})") from None


def _plazo(restante_ms) -> float:
    if restante_ms is None:
        return leer.PLAZO_LECTURA_S
    return min(leer.PLAZO_LECTURA_S, max(5.0, restante_ms() / 1000 - MARGEN_RESPUESTA_S))


def _difiere(p: dict, id_educadora: str, sala_grupo: str, fecha) -> list[str]:
    avisos = []
    if p["id_educadora"] and p["id_educadora"] != id_educadora:
        avisos.append("META_EXISTENTE_DIFIERE: id_educadora")
    if p["sala_grupo"] and p["sala_grupo"] != sala_grupo:
        avisos.append("META_EXISTENTE_DIFIERE: sala_grupo")
    if p["fecha_observacion"] and p["fecha_observacion"] != fecha:
        avisos.append("META_EXISTENTE_DIFIERE: fecha_observacion")
    return avisos


def _leer_meta(almacen, clave_meta: str) -> captura.MetaLeida:
    try:
        datos = almacen.leer_json(clave_meta)
    except almacen_mod.ObjetoNoEncontrado:
        raise Fallo("ERROR_ALMACENAMIENTO", "meta.json listado pero no legible") from None
    except (ValueError, almacen_mod.ObjetoDemasiadoGrande):
        log.warning("meta_invalida campo=json")
        raise Fallo("META_INVALIDA", "meta.json no es JSON valido") from None
    try:
        return captura.leer_meta_existente(datos)
    except captura.MetaInvalida as e:
        log.warning("meta_invalida campo=%s", e.campo)
        raise Fallo("META_INVALIDA", f"meta.json invalido: {e.campo}") from None


def _poligono_de_caja(caja, ancho: int, alto: int) -> np.ndarray:
    x0, y0, x1, y1 = (caja[0] * ancho / 1000, caja[1] * alto / 1000, caja[2] * ancho / 1000, caja[3] * alto / 1000)
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], np.float32)


def _orientacion(rgb: np.ndarray, detecciones, lector) -> tuple[int, bool, str]:
    """(índice de leer.GIROS, incierta, eje). El eje de la letra sale de los perfiles de proyección de la
    tinta de todos los recortes (recortar.eje_texto), sin el modelo: horizontal o dudoso -> 0°, sin llamar
    al modelo. Vertical -> el modelo elige solo entre 90° y 270° con los 2 post-its más grandes; si los
    votos no coinciden o no hay ninguno válido, la orientación es incierta y se queda en 0°."""
    eje, puntaje, contados = recortar.eje_texto([recortar.recortar_postit(rgb, d.poligono) for d in detecciones])
    log.info("eje_texto eje=%s puntaje=%.3f recortes=%d", eje, puntaje, contados)
    if eje != "vertical":
        return 0, False, eje
    if not hasattr(lector, "giro"):
        return 0, True, eje
    grandes = sorted(detecciones, key=lambda d: d.area_rel, reverse=True)[:2]
    recortes = [recortar.recortar_postit(rgb, d.poligono) for d in grandes]

    def votar(recorte):
        try:
            return lector.giro(recorte)
        except Exception as e:
            log.warning("giro_fallido tipo=%s", type(e).__name__)
            return None

    with ThreadPoolExecutor(max_workers=len(recortes)) as grupo:
        votos = list(grupo.map(votar, recortes))
    validos = [v for v in votos if v in leer.GIROS_VERTICAL]
    log.info("orientacion votos=%s", votos)
    if not validos or any(v != validos[0] for v in validos):
        return 0, True, eje
    return validos[0], False, eje


def procesar_captura(evento, *, almacen, lector, nomina, restante_ms=None) -> dict:
    """Procesa una petición directa (sección 6 del diseño). Nunca lanza: devuelve la respuesta o el error."""
    t0 = time.perf_counter()
    estado = {"id_captura": None}
    try:
        return _procesar(evento, almacen, lector, nomina, restante_ms, t0, estado)
    except Fallo as f:
        log.info("captura_error codigo=%s id_captura=%s", f.codigo, estado["id_captura"])
        respuesta = {"error": {"codigo": f.codigo, "mensaje": f.mensaje}}
    except Exception as e:  # bug: tipo y traza sin el mensaje (puede llevar datos)
        log.error("captura_error codigo=ERROR_INTERNO tipo=%s traza=%s", type(e).__name__,
                  "".join(traceback.format_tb(e.__traceback__))[-2000:])
        respuesta = {"error": {"codigo": "ERROR_INTERNO", "mensaje": f"error interno ({type(e).__name__})"}}
    if estado["id_captura"]:
        respuesta["id_captura"] = estado["id_captura"]
    return respuesta


def _procesar(evento, almacen, lector, nomina, restante_ms, t0, estado) -> dict:
    avisos: list[str] = []
    # 1. Petición
    try:
        p = captura.validar_peticion(evento)
    except captura.ErrorPeticion as e:
        log.info("peticion_rechazada campo=%s", e.campo)
        raise Fallo(e.codigo, f"campo invalido: {e.campo}") from None
    # 2. Id
    id_captura = p["id_captura"] or captura.nuevo_id_captura()
    estado["id_captura"] = id_captura
    pref = captura.prefijo(id_captura)
    clave_foto = captura.clave(id_captura, captura.RELATIVO_FOTO)
    clave_meta = captura.clave(id_captura, captura.RELATIVO_META)
    clave_texto = captura.clave(id_captura, captura.RELATIVO_TEXTO)
    # 3. Listado de la carpeta
    claves = _s3(almacen.listar, pref)
    # 3b. Origen
    if p["s3_key"] is None:
        origen = next((captura.clave(id_captura, r) for r in captura.ORIGENES_FOTO
                       if captura.clave(id_captura, r) in claves), None)
        if origen is None:
            raise Fallo("IMAGEN_NO_ENCONTRADA", "la captura no tiene original/foto.(jpg|jpeg|png)")
        tamano = claves[origen]
    elif p["s3_key"].startswith(pref):
        origen = p["s3_key"]
        if origen not in claves:
            raise Fallo("IMAGEN_NO_ENCONTRADA", "s3_key no existe")
        tamano = claves[origen]
    else:
        origen = p["s3_key"]
        md = _s3(almacen.metadatos, origen)
        if md is None:
            raise Fallo("IMAGEN_NO_ENCONTRADA", "s3_key no existe")
        tamano = md["tamano"]
    if tamano > MAX_ORIGEN:
        raise Fallo("IMAGEN_DEMASIADO_GRANDE", "la foto pesa mas de 25 MB")
    # 3c. Objetos que ya existen
    texto_existente = False
    if clave_texto in claves:
        md = _s3(almacen.metadatos, clave_texto)
        if md is None:
            raise Fallo("ERROR_ALMACENAMIENTO", "texto.json listado pero no legible")
        if md["meta"].get("origen") != almacen_mod.ORIGEN:
            log.info("peticion_rechazada campo=id_captura motivo=texto_ajeno")
            raise Fallo("PETICION_INVALIDA", "campo invalido: id_captura (ya tiene un texto.json ajeno)")
        texto_existente = True
    copiar = origen != clave_foto
    if copiar and clave_foto in claves:
        md = _s3(almacen.metadatos, clave_foto)
        if md is None:
            raise Fallo("ERROR_ALMACENAMIENTO", "original/foto.jpg listado pero no legible")
        if md["meta"].get("origen") == almacen_mod.ORIGEN and md["meta"].get("fuente") == origen:
            origen, copiar = clave_foto, False
        else:
            log.info("peticion_rechazada campo=s3_key motivo=foto_ajena")
            raise Fallo("PETICION_INVALIDA", "campo invalido: s3_key (la captura ya tiene otra foto)")
    # 4. Contexto
    meta_existe = clave_meta in claves
    if meta_existe:
        ml = _leer_meta(almacen, clave_meta)
        id_educadora, sala_grupo, fecha = ml.id_educadora, ml.sala_grupo, ml.fecha
        avisos.append("META_EXISTENTE")
        avisos += _difiere(p, id_educadora, sala_grupo, fecha)
        if ml.fecha_no_estandar:
            avisos.append("META_FECHA_NO_ESTANDAR")
    else:
        for campo in ("id_educadora", "sala_grupo"):
            if not p[campo]:
                log.info("peticion_rechazada campo=%s", campo)
                raise Fallo("PETICION_INVALIDA", f"campo invalido: {campo} (obligatorio sin meta.json)")
        id_educadora, sala_grupo = p["id_educadora"], p["sala_grupo"]
        fecha = p["fecha_observacion"] or captura.hoy_chile()
    # 5. Nómina (solo ayuda de lectura)
    try:
        try:
            ctx = nomina.contexto(id_educadora, sala_grupo, fecha, id_jardin=p["id_jardin"])
        except nomina_mod.JardinNoCoincide:
            if not meta_existe:
                raise Fallo("PETICION_INVALIDA", "campo invalido: id_jardin") from None
            avisos.append("ID_JARDIN_IGNORADO")
            ctx = nomina.contexto(id_educadora, sala_grupo, fecha)
    except Fallo:
        raise
    except Exception as e:  # red caída u otro error de AWS fuera de ClientError
        log.warning("nomina estado=no_disponible tipo=%s", type(e).__name__)
        ctx = nomina_mod.Contexto(None, [], "no_disponible", type(e).__name__)
    if not meta_existe and ctx.estado == "educadora_desconocida":
        raise Fallo("EDUCADORA_DESCONOCIDA", "la educadora no existe o no tiene jardin")
    if not meta_existe and ctx.estado == "sala_desconocida":
        raise Fallo("SALA_DESCONOCIDA", "la sala no tiene ninos vigentes")
    if ctx.estado != "ok":
        avisos.append(f"NOMINA_NO_DISPONIBLE: {ctx.detalle or ctx.estado.upper()}")
    ninos = ctx.ninos if ctx.estado == "ok" else []
    # 6. Foto
    try:
        datos = _s3(almacen.leer, origen, max_bytes=MAX_ORIGEN)
    except almacen_mod.ObjetoNoEncontrado:
        raise Fallo("IMAGEN_NO_ENCONTRADA", "no se pudo leer la foto") from None
    except almacen_mod.ObjetoDemasiadoGrande:
        raise Fallo("IMAGEN_DEMASIADO_GRANDE", "la foto pesa mas de 25 MB") from None
    try:
        foto = detectar.cargar_imagen(datos)
    except detectar.ImagenNoDecodificable as e:
        if e.heic:
            raise Fallo("FORMATO_NO_SOPORTADO", "HEIC/HEIF no soportado: sube JPEG") from None
        raise Fallo("IMAGEN_NO_DECODIFICABLE", "no se pudo decodificar la foto") from None
    rgb = foto.rgb
    alto, ancho = rgb.shape[:2]

    subidas = ThreadPoolExecutor(max_workers=4)
    futuros: list = []
    claves_subidas: list[str] = []

    def subir(clave_s3: str, contenido: bytes, metadatos: dict | None = None):
        claves_subidas.append(clave_s3)
        futuros.append(subidas.submit(almacen.guardar, clave_s3, contenido, TIPO_JPEG, metadatos=metadatos))

    def esperar_subidas():
        for futuro in futuros:
            _s3(futuro.result)

    try:
        # 6b. Copia de la foto completa a original/foto.jpg
        if copiar:
            if datos[:3] == b"\xff\xd8\xff":
                bytes_foto = datos
            else:
                ok, cod = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
                if not ok:
                    raise Fallo("IMAGEN_NO_DECODIFICABLE", "no se pudo recodificar la foto")
                bytes_foto = cod.tobytes()
            subir(clave_foto, bytes_foto, {"fuente": origen})
        # 7. Detección y orientación (una por foto: la letra suele estar girada igual en todos los post-its)
        t_det = time.perf_counter()
        detecciones = [] if p["modo"] == "llm" else detectar.detectar_postits(rgb)
        giro, orientacion_incierta, eje = 0, False, None
        if detecciones:
            giro, orientacion_incierta, eje = _orientacion(rgb, detecciones, lector)
            if orientacion_incierta:
                avisos.append("ORIENTACION_INCIERTA")
            if giro:
                rgb = cv2.rotate(rgb, leer.GIROS[giro])
                alto, ancho = rgb.shape[:2]
                detecciones = detectar.detectar_postits(rgb)
        detecciones = [detecciones[i] for i in recortar.orden_lectura([d.poligono for d in detecciones])]
        partes: list[dict] = []
        if detecciones:
            # 8. Rama opencv
            modo = "opencv"
            rgb_recortes = [recortar.recortar_postit(rgb, d.poligono) for d in detecciones]
            recortes = [recortar.codificar_jpeg(r) for r in rgb_recortes]  # los que se guardan en S3
            para_leer = [leer.preparar_recorte_llm(r) for r in rgb_recortes]  # ampliados para el modelo
            overlay = recortar.dibujar_overlay(rgb, [(d.poligono, d.color, n) for n, d in enumerate(detecciones, 1)])
            ms_deteccion = int((time.perf_counter() - t_det) * 1000)
            for n, recorte in enumerate(recortes, 1):
                subir(captura.clave(id_captura, captura.relativo_postit(n)), recorte)
            subir(captura.clave(id_captura, captura.RELATIVO_OVERLAY), overlay)
            t_lec = time.perf_counter()
            if orientacion_incierta:  # sin orientación clara no se lee: nunca un texto adivinado
                lecturas = [{"texto": leer.ILEGIBLE, "legibilidad": "baja"} for _ in recortes]
            else:
                lecturas = leer.leer_recortes(para_leer, ninos, lector,
                                              [{"orden": n} for n in range(1, len(recortes) + 1)],
                                              plazo_s=_plazo(restante_ms))
            ms_lectura = int((time.perf_counter() - t_lec) * 1000)
            fallidas = 0
            for n, (d, lectura) in enumerate(zip(detecciones, lecturas), 1):
                if lectura.get("error"):
                    fallidas += 1
                    avisos.append(f"LECTURA_FALLIDA: orden {n} ({lectura['error']})")
                    texto, legibilidad = leer.ILEGIBLE, "baja"
                else:
                    texto, legibilidad = lectura["texto"], lectura["legibilidad"]
                    if lectura.get("no_json"):
                        avisos.append(f"LECTURA_NO_JSON: orden {n}")
                partes.append({"orden": n, "archivo": captura.relativo_postit(n), "texto": texto,
                               "legibilidad": legibilidad, "color": d.color})
            if fallidas == len(detecciones):
                esperar_subidas()
                raise Fallo("LECTURA_NO_DISPONIBLE", "fallaron todas las lecturas; reintenta con el mismo id_captura")
        else:
            # 9. Plan B: el modelo lee la foto completa
            modo = "llm"
            avisos.append("PLAN_B: modo llm" if p["modo"] == "llm" else "PLAN_B: opencv no detecto post-its")
            foto_llm = leer.preparar_foto_llm(rgb)
            ms_deteccion = int((time.perf_counter() - t_det) * 1000)
            t_lec = time.perf_counter()
            try:
                postits = leer.leer_foto(foto_llm, ninos, lector, plazo_s=_plazo(restante_ms))
            except Exception as e:
                log.warning("plan_b_fallido tipo=%s", type(e).__name__)
                esperar_subidas()
                raise Fallo("LECTURA_NO_DISPONIBLE", "fallo la lectura de la foto completa; reintenta") from None
            ms_lectura = int((time.perf_counter() - t_lec) * 1000)
            poligonos = None
            if postits and all(pt.get("caja") for pt in postits):
                poligonos = [_poligono_de_caja(pt["caja"], ancho, alto) for pt in postits]
                orden = recortar.orden_lectura(poligonos)
                postits, poligonos = [postits[i] for i in orden], [poligonos[i] for i in orden]
            elementos = [(_poligono_de_caja(pt["caja"], ancho, alto), pt["color"], n)
                         for n, pt in enumerate(postits, 1) if pt.get("caja")]
            subir(captura.clave(id_captura, captura.RELATIVO_OVERLAY), recortar.dibujar_overlay(rgb, elementos))
            if not postits:
                avisos.append("SIN_POSTITS")
            for n, pt in enumerate(postits, 1):
                partes.append({"orden": n, "archivo": captura.RELATIVO_FOTO, "texto": pt["texto"],
                               "legibilidad": pt["legibilidad"], "color": pt["color"]})
        if getattr(lector, "sin_temperatura", False):
            avisos.append("TEMPERATURA_NO_SOPORTADA")
        # 10. Todas las imágenes escritas antes de cualquier JSON
        t_sub = time.perf_counter()
        esperar_subidas()
    finally:
        subidas.shutdown(wait=True)

    # 11. Freno: una parte con legibilidad baja va como [ilegible] (ProcesarNota no le asigna niño) y queda en
    # no_leidos, para que la web muestre su recorte y la educadora la escriba a mano.
    no_leidos = []
    for parte in partes:
        if parte["legibilidad"] == "baja":
            parte["texto"] = leer.ILEGIBLE
        if parte["texto"] == leer.ILEGIBLE:
            no_leidos.append({"orden": parte["orden"], "archivo": parte["archivo"]})
    if no_leidos:
        avisos.append(f"LECTURA_BAJA: {len(no_leidos)}")

    # 12. Documentos
    claves_disponibles = set(claves_subidas)
    if not copiar:
        claves_disponibles.add(clave_foto)  # el origen ya era original/foto.jpg (Plan B apunta ahí)
    texto_doc = captura.armar_texto(id_captura, partes)
    captura.validar_texto(texto_doc, id_captura, claves_disponibles)
    meta_doc = None if meta_existe else captura.armar_meta(id_educadora, sala_grupo, fecha)

    # 13. Escritura: meta.json (si no existe) y texto.json al final
    meta_escrito = texto_escrito = False
    if p["escribir_texto"]:
        if meta_doc is not None:
            if not almacen.escritura_condicional:
                avisos.append("ESCRITURA_NO_CONDICIONAL")
            meta_escrito = _s3(almacen.guardar, clave_meta, _json_bytes(meta_doc), TIPO_JSON, solo_si_no_existe=True)
            if not meta_escrito:  # otro proceso lo escribió entre el listado y la escritura
                ml = _leer_meta(almacen, clave_meta)
                avisos.append("META_EXISTENTE")
                avisos += _difiere(p, ml.id_educadora, ml.sala_grupo, ml.fecha)
        _s3(almacen.guardar, clave_texto, _json_bytes(texto_doc), TIPO_JSON)
        texto_escrito = True
        if texto_existente:
            avisos.append("TEXTO_REESCRITO")
    ms_subida = int((time.perf_counter() - t_sub) * 1000)

    respuesta = {
        "id_captura": id_captura, "prefijo": pref, "n_postits": len(partes), "modo": modo,
        "giro_grados": (0, 90, 180, 270)[giro], "partes": partes, "no_leidos": no_leidos,
        "tiempos_ms": {"deteccion": ms_deteccion, "lectura": ms_lectura, "subida": ms_subida,
                       "total": int((time.perf_counter() - t0) * 1000)},
        "meta_escrito": bool(meta_escrito), "texto_escrito": texto_escrito, "avisos": avisos,
    }
    if not p["escribir_texto"]:
        respuesta["documentos"] = {"meta.json": meta_doc, "texto.json": texto_doc}
    if p["incluir_urls"]:
        try:
            for parte in partes:
                parte["url"] = almacen.url(captura.clave(id_captura, parte["archivo"]))
            respuesta["overlay_url"] = almacen.url(captura.clave(id_captura, captura.RELATIVO_OVERLAY))
        except Exception as e:
            log.warning("urls_no_disponibles tipo=%s", type(e).__name__)
            avisos.append("URLS_NO_DISPONIBLES")
    log.info(json.dumps({
        "evento": "captura", "id_captura": id_captura, "origen": "directo", "modo": modo, "n_postits": len(partes),
        "giro_grados": respuesta["giro_grados"], "eje": eje,
        "lecturas_fallidas": sum(1 for a in avisos if a.startswith("LECTURA_FALLIDA")),
        "legibilidad_baja": sum(1 for pt in partes if pt["legibilidad"] == "baja"), "no_leidos": len(no_leidos),
        "meta_escrito": respuesta["meta_escrito"], "texto_escrito": texto_escrito, "ensayo": not p["escribir_texto"],
        "avisos": sorted({a.split(":")[0] for a in avisos}), "ms": respuesta["tiempos_ms"]}))
    return respuesta


# ----------------------------------------------------------------------------- Lambda

_RECURSOS: dict = {}


def _recursos() -> dict:
    """Clientes y lector, uno por contenedor (boto3 es thread-safe con clientes)."""
    if not _RECURSOS:
        almacen = almacen_mod.AlmacenS3(os.environ["POSTITS_BUCKET"])
        fuente = os.environ.get("POSTITS_FUENTE_NOMINA", "").strip().lower()
        tablas = os.environ.get("TABLA_EDUCADORAS") and os.environ.get("TABLA_NINOS")
        if fuente == "aws" or (fuente != "local" and tablas):
            nomina = nomina_mod.NominaDynamo(os.environ["TABLA_EDUCADORAS"], os.environ["TABLA_NINOS"])
        else:
            nomina = nomina_mod.NominaLocal()
        _RECURSOS.update(almacen=almacen, nomina=nomina, lector=leer.LectorBedrock())
        log.info(json.dumps({**_INICIO, "escritura_condicional": almacen.escritura_condicional,
                             "modelo": _RECURSOS["lector"].modelo}))
    return _RECURSOS


def handler(event, context=None):
    if isinstance(event, dict) and isinstance(event.get("Records"), list):
        log.info("evento_s3 estado=ignorada registros=%d", len(event["Records"]))
        return {"procesados": [{"id_captura": None, "estado": "ignorada", "motivo": "disparador S3 no habilitado"}
                               for _ in event["Records"]]}
    peticion = event
    if isinstance(event, dict) and "body" in event:
        try:
            peticion = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        except ValueError:
            log.info("peticion_rechazada campo=body")
            return {"error": {"codigo": "PETICION_INVALIDA", "mensaje": "campo invalido: body"}}
    if not os.environ.get("POSTITS_BUCKET"):
        log.error("configuracion falta=POSTITS_BUCKET")
        return {"error": {"codigo": "CONFIGURACION", "mensaje": "falta POSTITS_BUCKET"}}
    r = _recursos()
    restante = getattr(context, "get_remaining_time_in_millis", None)
    return procesar_captura(peticion, almacen=r["almacen"], lector=r["lector"], nomina=r["nomina"],
                            restante_ms=restante)
