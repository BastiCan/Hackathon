"""Escritura de capturas: `POST /api/capturas` y `POST /api/capturas/{id}/archivar`.

Pasos de `POST /api/capturas` (SPEC-OFICIAL.md §1, CONTRATOS.md §3): validar,
reservar cupo del día, crear la fila en `enviando`, escribir `meta.json` y
después `texto.json` (o enviar el audio al transcriptor), marcar `enviada` y
responder 201 con la evidencia en `procesando`. Si falla una escritura, la fila
queda en `error_envio` y la respuesta es 502.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Response
from pydantic import BaseModel, ConfigDict

from .. import auth, errores, s3, tiempo, ulid
from ..config import Config, cargar_config
from ..datos import audio, capturas
from ..modelos import CapturaCreada, CapturaEntrada, Evidencia
from . import PREFIJO

FORMATOS = ("texto", "audio")
LARGO_MAX_TEXTO = 5000

CFG: Config = cargar_config()

router = APIRouter(prefix=PREFIJO, tags=["capturas"])


Cabecera = Annotated[str | None, Header(alias=auth.CABECERA_USUARIA)]


def configurar(cfg: Config) -> None:
    """Recibe la config que `app.py` carga una sola vez al arrancar."""
    global CFG  # noqa: PLW0603 - la config del despliegue es única
    CFG = cfg


class ArchivarEntrada(BaseModel):
    """Cuerpo de `POST /api/capturas/{id}/archivar`."""

    model_config = ConfigDict(extra="forbid")

    salaId: str  # noqa: N815 - camelCase como el resto de la API


def _texto_o_error(entrada: CapturaEntrada) -> str:
    """Texto recortado de 1 a 5000 caracteres, o `texto_invalido` (422)."""
    texto = (entrada.texto or "").strip()
    if not texto or len(texto) > LARGO_MAX_TEXTO:
        raise errores.error("texto_invalido")
    return texto


def _revisar_audio(entrada: CapturaEntrada) -> None:
    """Valida el base64 (422) y el tamaño decodificado, hasta 4 MiB (413)."""
    if not entrada.audioBase64:
        raise errores.error("base64_invalido")
    audio.decodificar(entrada.audioBase64)


def _entregar(id_captura: str, entrada: CapturaEntrada, dia: str, texto: str | None) -> None:
    """`meta.json` primero y `texto.json` después. Un fallo de escritura deja la
    fila en `error_envio` y responde 502; el audio lo entrega el transcriptor,
    que trae sus propios códigos."""
    try:
        s3.subir_json(CFG, s3.clave_meta(id_captura), s3.cuerpo_meta(entrada.autorId, entrada.salaId, dia))
        if texto is not None:
            s3.subir_json(CFG, s3.clave_texto(id_captura), s3.cuerpo_texto(id_captura, texto, "manual"))
    except Exception as falla:
        capturas.marcar_envio(CFG, id_captura, "error_envio")
        raise errores.error("error_envio") from falla
    if entrada.formato == "audio":
        audio.enviar(CFG, id_captura, entrada.audioBase64 or "")


@router.post(
    "/capturas",
    status_code=201,
    response_model=CapturaCreada,
    response_model_exclude_none=True,
)
def crear_captura(entrada: CapturaEntrada, id_usuaria: Cabecera = None) -> CapturaCreada:
    """Guarda la nota de la tía y la deja camino a ProcesarNota."""
    if not auth.existe(entrada.autorId):
        raise errores.error("autora_desconocida")
    usuaria = auth.usuaria_o_error(id_usuaria)
    auth.exigir_sala(CFG, usuaria, entrada.salaId)
    if entrada.autorId != usuaria.id:
        raise errores.error("sin_acceso")
    if entrada.formato not in FORMATOS:
        raise errores.error("formato_no_soportado")
    texto = _texto_o_error(entrada) if entrada.formato == "texto" else None
    if entrada.formato == "audio":
        _revisar_audio(entrada)

    momento = tiempo.ahora(CFG)
    dia = tiempo.dia(momento)
    creada_en = tiempo.iso(momento)
    capturas.reservar_cupo_del_dia(CFG, entrada.salaId, dia)

    id_captura = ulid.nuevo_id_captura()
    capturas.crear_fila(
        CFG,
        id_captura=id_captura,
        sala_id=entrada.salaId,
        autor_id=entrada.autorId,
        formato=entrada.formato,
        creada_en=creada_en,
        dia=dia,
        nino_id_sugerido=entrada.ninoIdSugerido,
        mime_type=entrada.mimeType,
    )
    if texto is not None:
        capturas.guardar_texto(CFG, id_captura, texto)
    _entregar(id_captura, entrada, dia, texto)
    capturas.marcar_envio(CFG, id_captura, "enviada")

    return CapturaCreada(
        evidencia=Evidencia(
            id=id_captura,
            salaId=entrada.salaId,
            autorId=entrada.autorId,
            creadaEn=creada_en,
            formato=entrada.formato,
            ninoIdSugerido=entrada.ninoIdSugerido,
            textoExtraido=texto,
            estado="procesando",
        )
    )


@router.post("/capturas/{id_captura}/archivar", status_code=204)
def archivar_captura(id_captura: str, entrada: ArchivarEntrada, id_usuaria: Cabecera = None) -> Response:
    """Archiva la captura y la deja `lista`. Responde 204 sin cuerpo."""
    usuaria = auth.usuaria_o_error(id_usuaria)
    auth.exigir_sala(CFG, usuaria, entrada.salaId)
    if not capturas.archivar(CFG, id_captura, entrada.salaId):
        raise errores.error("no_encontrado")
    return Response(status_code=204)
