"""API FastAPI del Desafío 1 Integra.

Endpoints principales:
- GET  /api/jardines                              lista de jardines
- GET  /api/jardines/{id}/salas                   salas de un jardín
- GET  /api/salas/{id_jardin}/{sala}/ninos        vista de sala con semáforo
- GET  /api/salas/{id_jardin}/{sala}/mision       misión del día
- GET  /api/ninos/{id}                            ficha del niño (trayectoria)
- GET  /api/ninos/{id}/alertas                    alertas del niño
- GET  /api/ruta                                  ruta de niveles
- POST /api/capturas/procesar                     IA: procesa una captura de texto
"""
from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .data import get_store
from .models import (
    Alerta,
    CapturaRequest,
    MisionItem,
    NinoEstado,
    NivelRuta,
    Observacion,
    ProcesarCapturaResponse,
)
from .services import ai, analytics

# Fecha de referencia del dataset (ver README del dataset).
HOY = date(2026, 10, 13)

app = FastAPI(
    title="Integra · Desafío 1 — API",
    description="Documentación pedagógica asistida por IA para educadoras de párvulos.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    store = get_store()
    return {
        "status": "ok",
        "ninos": str(len(store.ninos)),
        "observaciones": str(len(store.observaciones)),
    }


@app.get("/api/jardines")
def listar_jardines():
    store = get_store()
    return list(store.jardines.values())


@app.get("/api/jardines/{id_jardin}/salas")
def listar_salas(id_jardin: str) -> list[str]:
    store = get_store()
    if id_jardin not in store.jardines:
        raise HTTPException(404, "Jardín no encontrado")
    salas = sorted({n.sala_grupo for n in store.ninos_de_jardin(id_jardin)})
    return salas


@app.get("/api/salas/{id_jardin}/{sala}/ninos", response_model=list[NinoEstado])
def ninos_de_sala(id_jardin: str, sala: str):
    store = get_store()
    ninos = store.ninos_de_sala(id_jardin, sala)
    if not ninos:
        raise HTTPException(404, "Sala sin niños o inexistente")
    return [analytics.estado_nino(store, n, HOY) for n in ninos]


@app.get("/api/salas/{id_jardin}/{sala}/mision", response_model=list[MisionItem])
def mision(id_jardin: str, sala: str):
    store = get_store()
    return analytics.mision_del_dia(store, id_jardin, sala, HOY)


@app.get("/api/ninos/{id_nino}")
def ficha_nino(id_nino: str):
    store = get_store()
    nino = store.ninos.get(id_nino)
    if not nino:
        raise HTTPException(404, "Niño no encontrado")
    estado = analytics.estado_nino(store, nino, HOY)
    observaciones = store.observaciones_de(id_nino)
    alertas = analytics.detectar_alertas(store, nino, HOY)
    return {
        "estado": estado,
        "observaciones": observaciones,
        "alertas": alertas,
    }


@app.get("/api/ninos/{id_nino}/alertas", response_model=list[Alerta])
def alertas_nino(id_nino: str):
    store = get_store()
    nino = store.ninos.get(id_nino)
    if not nino:
        raise HTTPException(404, "Niño no encontrado")
    return analytics.detectar_alertas(store, nino, HOY)


@app.get("/api/ruta", response_model=list[NivelRuta])
def ruta_niveles():
    store = get_store()
    return [store.niveles[k] for k in sorted(store.niveles)]


@app.post("/api/capturas/procesar", response_model=ProcesarCapturaResponse)
def procesar_captura(req: CapturaRequest):
    store = get_store()
    # Para la demo usamos la sala del primer jardín como contexto de identificación.
    # En producción vendría del contexto de sesión de la educadora.
    primer_jardin = next(iter(store.jardines))
    salas = sorted({n.sala_grupo for n in store.ninos_de_jardin(primer_jardin)})
    ninos_sala = store.ninos_de_sala(primer_jardin, salas[0]) if salas else []
    sugerencias = ai.procesar_captura(store, req.texto, ninos_sala, HOY)
    return ProcesarCapturaResponse(sugerencias=sugerencias)
