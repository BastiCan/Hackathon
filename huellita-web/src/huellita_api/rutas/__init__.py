"""Routers HTTP del BFF (`lectura`, `capturas`, `decisiones`), todos bajo /api.

El prefijo vive acá y no en `app.py` para que cada router declare sus rutas completas: así
`app.routes` lleva las rutas del contrato tal como las pide la tía (`/api/salud`,
`/api/capturas`, …) y no una envoltura que haya que desarmar para saber qué quedó montado.
"""

#: Base de toda la API, igual que `BASE` del frontend (CONTRATOS.md §4).
PREFIJO = "/api"
