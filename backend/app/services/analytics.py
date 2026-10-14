"""Lógica de dominio: edad, estado por niño (semáforo) y detección de rezagos.

Implementa las ideas de la sección 4 de la síntesis:
- Dos alertas distintas: "sin evidencia reciente" vs "posible rezago".
- Señales de rezago: bajo lo esperado para la edad, estancamiento, retroceso.
- Confirmación: se requiere más de una observación coincidente.
"""
from __future__ import annotations

from datetime import date

from ..config import MIN_OBS_TO_CONFIRM, WEEKS_WITHOUT_EVIDENCE
from ..data import DataStore
from ..models import Alerta, MisionItem, Nino, NinoEstado, Observacion


def edad_meses(fecha_nacimiento: date, referencia: date) -> int:
    """Edad en meses completos (misma fórmula que el diccionario de datos)."""
    meses = 12 * (referencia.year - fecha_nacimiento.year) + (
        referencia.month - fecha_nacimiento.month
    )
    if referencia.day < fecha_nacimiento.day:
        meses -= 1
    return max(meses, 0)


def nivel_esperado_para_edad(store: DataStore, meses: int) -> int | None:
    """Nivel cuyo rango de edad contiene los meses dados (el más alto que aplique)."""
    candidatos = [
        n.nivel
        for n in store.niveles.values()
        if n.edad_min_meses <= meses <= n.edad_max_meses
    ]
    if candidatos:
        return max(candidatos)
    # Fuera de rango: por encima del tope → último nivel; por debajo → primero.
    niveles_ord = sorted(store.niveles.values(), key=lambda n: n.nivel)
    if meses > niveles_ord[-1].edad_max_meses:
        return niveles_ord[-1].nivel
    return niveles_ord[0].nivel


def _dias_entre(a: date, b: date) -> int:
    return abs((b - a).days)


def estado_nino(store: DataStore, nino: Nino, hoy: date) -> NinoEstado:
    obs = store.observaciones_de(nino.id_nino)
    meses = edad_meses(nino.fecha_nacimiento, hoy)
    ultima = obs[-1].fecha_observacion if obs else None
    nivel_actual = obs[-1].nivel_estimado if obs else None
    dias_sin = _dias_entre(ultima, hoy) if ultima else None

    estado = _clasificar_estado(store, nino, obs, meses, hoy, dias_sin)

    return NinoEstado(
        nino=nino,
        edad_meses=meses,
        ultima_observacion=ultima,
        nivel_actual=nivel_actual,
        estado=estado,
        dias_sin_evidencia=dias_sin,
    )


def _clasificar_estado(
    store: DataStore,
    nino: Nino,
    obs: list[Observacion],
    meses: int,
    hoy: date,
    dias_sin: int | None,
) -> str:
    # Ingreso reciente o datos insuficientes.
    if len(obs) < 2:
        # Si ingresó hace poco, es "ingreso reciente"; si no, "sin evidencia".
        if _dias_entre(nino.fecha_ingreso, hoy) <= 30:
            return "ingreso_reciente"
        return "sin_evidencia"

    # Sin evidencia reciente.
    if dias_sin is not None and dias_sin > WEEKS_WITHOUT_EVIDENCE * 7:
        return "sin_evidencia"

    # Posible rezago: nivel actual bajo lo esperado para la edad.
    esperado = nivel_esperado_para_edad(store, meses)
    nivel_actual = obs[-1].nivel_estimado
    if esperado is not None and nivel_actual < esperado - 1:
        return "posible_rezago"

    return "al_dia"


def detectar_alertas(store: DataStore, nino: Nino, hoy: date) -> list[Alerta]:
    """Devuelve las alertas confirmadas/no confirmadas de un niño."""
    alertas: list[Alerta] = []
    obs = store.observaciones_de(nino.id_nino)
    meses = edad_meses(nino.fecha_nacimiento, hoy)

    # Alerta 🟡 sin evidencia reciente.
    if not obs:
        alertas.append(
            Alerta(
                id_nino=nino.id_nino,
                tipo="sin_evidencia",
                severidad="media",
                mensaje="No hay observaciones registradas para este niño/a.",
                accion_sugerida="Obsérvalo: aún nadie ha registrado evidencia.",
                nucleos_afectados=[],
                confirmada=False,
            )
        )
        return alertas

    dias_sin = _dias_entre(obs[-1].fecha_observacion, hoy)
    if dias_sin > WEEKS_WITHOUT_EVIDENCE * 7:
        alertas.append(
            Alerta(
                id_nino=nino.id_nino,
                tipo="sin_evidencia",
                severidad="media",
                mensaje=f"Sin evidencia hace {dias_sin} días.",
                accion_sugerida="Obsérvalo en la próxima rutina de juego.",
                nucleos_afectados=[],
                confirmada=False,
            )
        )

    # Alerta 🔴 posible rezago (bajo lo esperado para la edad).
    esperado = nivel_esperado_para_edad(store, meses)
    niveles_recientes = [o.nivel_estimado for o in obs[-MIN_OBS_TO_CONFIRM:]]
    if esperado is not None and all(n < esperado - 1 for n in niveles_recientes):
        confirmada = len(niveles_recientes) >= MIN_OBS_TO_CONFIRM
        alertas.append(
            Alerta(
                id_nino=nino.id_nino,
                tipo="posible_rezago",
                severidad="alta" if confirmada else "media",
                mensaje=(
                    f"Nivel actual {niveles_recientes[-1]} bajo lo esperado "
                    f"({esperado}) para {meses} meses."
                ),
                accion_sugerida=(
                    "Atención con su desarrollo. Realiza una observación dirigida "
                    "para confirmar."
                ),
                nucleos_afectados=["general"],
                confirmada=confirmada,
            )
        )

    # Retroceso entre observaciones confirmadas.
    if len(obs) >= 2 and obs[-1].nivel_estimado < obs[-2].nivel_estimado:
        alertas.append(
            Alerta(
                id_nino=nino.id_nino,
                tipo="posible_rezago",
                severidad="media",
                mensaje=(
                    f"Retroceso de nivel {obs[-2].nivel_estimado} a "
                    f"{obs[-1].nivel_estimado}."
                ),
                accion_sugerida="Verifica con una nueva observación dirigida.",
                nucleos_afectados=["general"],
                confirmada=False,
            )
        )

    return alertas


def mision_del_dia(
    store: DataStore, id_jardin: str, sala_grupo: str, hoy: date, limite: int = 5
) -> list[MisionItem]:
    """Sugiere niños a observar hoy: sin evidencia o con posible rezago."""
    items: list[MisionItem] = []
    for nino in store.ninos_de_sala(id_jardin, sala_grupo):
        estado = estado_nino(store, nino, hoy)
        if estado.estado in ("sin_evidencia", "posible_rezago", "ingreso_reciente"):
            siguiente = (estado.nivel_actual or 0) + 1
            manifs = store.manifestaciones_de_nivel(siguiente)
            que = manifs[0].texto_observable if manifs else None
            dom = manifs[0].dominio if manifs else None
            motivo = {
                "sin_evidencia": "Sin evidencia reciente",
                "posible_rezago": "Posible rezago, requiere confirmación",
                "ingreso_reciente": "Ingreso reciente, falta línea base",
            }[estado.estado]
            items.append(
                MisionItem(
                    id_nino=nino.id_nino,
                    motivo=motivo,
                    dominio_sugerido=dom,
                    que_observar=que,
                )
            )
        if len(items) >= limite:
            break
    return items
