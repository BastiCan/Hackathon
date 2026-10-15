"""Aplicación FastAPI del BFF de Huellita: configuración, CORS, errores y handler de Lambda.

`cargar_config()` se llama una sola vez, aquí, al importar el módulo: el `Config` resultante
(`CFG`) es el que usan las rutas. Cualquier excepción que llegue hasta acá sale con la forma
`{"error": {"codigo", "mensaje"}}` y en las palabras de la tía: nunca viajan trazas, nombres
de tablas, ARNs ni mensajes de botocore.
"""
from __future__ import annotations

import logging
from types import ModuleType

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from mangum import Mangum
from starlette.exceptions import HTTPException as ErrorHttpStarlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request

from huellita_api import auth, errores
from huellita_api.config import cargar_config
from huellita_api.modelos import DetalleError, RespuestaError
from huellita_api.rutas import capturas, decisiones, lectura

_LOG = logging.getLogger("huellita_api")

#: Mensaje de reserva, por si un código no estuviera en `errores.MENSAJES`.
_MENSAJE_GENERICO = "No pudimos hacer esto. Intenta de nuevo."

#: Los tres routers del BFF, en el orden en que se montan. Cada uno ya trae el prefijo
#: `/api` (ver `rutas/__init__.py`), así que `app.routes` queda con las rutas del contrato.
ROUTERS: tuple[ModuleType, ...] = (lectura, capturas, decisiones)

#: Config del despliegue. Se define antes de montar los routers porque alguno la lee al
#: importarse (`from huellita_api.app import CFG`).
CFG = cargar_config()

app = FastAPI(title="Huellita BFF")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type", auth.CABECERA_USUARIA],
)


def respuesta_error(codigo: str, mensaje: str | None = None, estado: int | None = None) -> JSONResponse:
    """La única forma de error del BFF: `modelos.RespuestaError` con su estado HTTP estable."""
    cuerpo = RespuestaError(
        error=DetalleError(codigo=codigo, mensaje=mensaje or errores.MENSAJES.get(codigo, _MENSAJE_GENERICO))
    )
    return JSONResponse(status_code=estado or errores.estado_http(codigo), content=cuerpo.model_dump())


@app.exception_handler(errores.ErrorApi)
async def manejar_error_api(solicitud: Request, excepcion: errores.ErrorApi) -> JSONResponse:
    """Los errores esperados viajan con su código estable y su mensaje para la tía."""
    return respuesta_error(excepcion.codigo, excepcion.mensaje)


@app.exception_handler(RequestValidationError)
async def manejar_validacion(solicitud: Request, excepcion: RequestValidationError) -> JSONResponse:
    """Cuerpo que no valida (pydantic): `solicitud_invalida`, sin el detalle del validador."""
    return respuesta_error("solicitud_invalida")


@app.exception_handler(ErrorHttpStarlette)
async def manejar_http(solicitud: Request, excepcion: ErrorHttpStarlette) -> JSONResponse:
    """Ruta o método que no existe: `no_encontrado`. El resto conserva su estado HTTP."""
    if excepcion.status_code in (404, 405):
        return respuesta_error("no_encontrado")
    codigo = "error_interno" if excepcion.status_code >= 500 else "solicitud_invalida"
    return respuesta_error(codigo, estado=excepcion.status_code)


@app.exception_handler(Exception)
async def manejar_inesperado(solicitud: Request, excepcion: Exception) -> JSONResponse:
    """Cualquier otra excepción: `error_interno`. El detalle queda en el log, no en la respuesta."""
    _LOG.exception("error inesperado atendiendo %s", getattr(solicitud, "url", "la petición"))
    return respuesta_error("error_interno")


def pasar_config(modulo: ModuleType) -> bool:
    """Si el router expone `configurar(cfg)`, le pasa `CFG`: la config se lee una sola vez."""
    configurar = getattr(modulo, "configurar", None)
    if not callable(configurar):
        return False
    configurar(CFG)
    return True


def incluir_routers() -> list[str]:
    """Monta los tres routers y devuelve los nombres montados.

    Las rutas se agregan planas a `app.router.routes` en vez de con `include_router`: desde
    FastAPI 0.137 incluir un router deja una envoltura perezosa en `app.routes` que no tiene
    `path`, y el contrato del BFF se revisa justamente mirando las rutas montadas.
    """
    montados: list[str] = []
    for modulo in ROUTERS:
        pasar_config(modulo)
        app.router.routes.extend(modulo.router.routes)
        montados.append(modulo.__name__.rpartition(".")[2])
    return montados


ROUTERS_INCLUIDOS = incluir_routers()

#: Entrada de Lambda (`huellita_api.app.handler`), sin eventos de arranque ni apagado.
handler = Mangum(app, lifespan="off")
