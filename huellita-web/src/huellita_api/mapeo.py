"""Las reglas 1 a 8 del spec, como funciones puras: de ítem de DynamoDB a modelo de la API.

Sin boto3, sin red y sin leer el entorno. Los criterios que comparte con el modo local del
frontend (separar homónimos, mediana baja de la edad, cita del historial) son los mismos de
`huellita-formato-mejorado/scripts/generar_datos_e1.py`, así las dos versiones de Huellita
muestran lo mismo.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime

from . import tiempo
from .config import Config
from .modelos import NUCLEOS, Evidencia, EstadoEvidencia, Jardin, Nino, NivelEducativo, Sala, Sugerencia

# Regla 1: tramos de edad en meses -> nivel educativo de la sala.
TRAMOS_NIVEL: tuple[tuple[int, str], ...] = (
    (12, "Sala Cuna Menor"),
    (24, "Sala Cuna Mayor"),
    (36, "Medio Menor"),
    (48, "Medio Mayor"),
    (60, "Transición 1"),
)
NIVEL_MAS_ALTO = "Transición 2"
NIVEL_SIN_NINOS = "Sala Cuna Menor"

# Regla 4: el historial del dataset no tiene hora, el generador local le pone mediodía.
HORA_HISTORIAL = "12:00:00"
HUSO_HISTORIAL = "-03:00"
SEPARADOR_HISTORIAL = "~"

# Regla 5: una captura sin fila en Capturas es audio si su objeto está bajo original/audio.
RUTA_AUDIO = "original/audio"

# DECISIÓN ABIERTA del spec (§7): el primer candidato de una nota NO_IDENTIFICADO puede no
# tener nada que ver con el nombre que escribió la tía ("Agustín" -> "Martina R.", 77).
# Mientras se decide se sigue la regla tal cual: subir este umbral es el único cambio.
UMBRAL_PUNTAJE_CANDIDATO = 0

ORDEN_CERTEZA: dict[str, int] = {"alta": 0, "media": 1, "baja": 2}
CERTEZA_SIN_DATO = len(ORDEN_CERTEZA)
CERTEZAS: tuple[str, ...] = tuple(ORDEN_CERTEZA)
FORMATOS: tuple[str, ...] = ("foto", "audio", "texto")
ESTADOS_FINALES: tuple[str, ...] = ("lista", "error")
NIVEL_MINIMO = 1
NIVEL_MAXIMO = 9

# Regla 6: estados de la tabla Registros de integra-procesador -> estado para la tía.
ESTADOS_REGISTRO: dict[str, EstadoEvidencia] = {
    "RECIBIDO": "procesando",
    "PROCESANDO": "procesando",
    "PROCESADO": "lista",
    "SIN_TEXTO": "error",
    "ERROR": "error",
}

# Regla 5: notas que la IA no pudo evaluar. La conducta explica el motivo para que la tía
# corrija o descarte.
CONDUCTA_SIN_EVALUAR = "No pudimos evaluar esta nota. Revísala y corrige si corresponde."
MOTIVOS_NO_EVALUABLE: dict[str, str] = {
    "ESTADO_O_SALUD": "La nota cuenta cómo estuvo el niño o la niña, no una conducta que podamos evaluar.",
    "JUICIO_SIN_CONDUCTA": "La nota da una impresión general, sin una conducta concreta que podamos evaluar.",
    "CONDUCTA_ADULTO": "La nota cuenta lo que hizo una persona adulta, no el niño o la niña.",
    "LOGISTICA_O_FAMILIA": "La nota es de organización o de la familia, no una conducta del niño o la niña.",
    "OTRO": CONDUCTA_SIN_EVALUAR,
}

_HOMONIMO = re.compile(r"^(.+?)\s+([A-ZÁÉÍÓÚÑ])\.$")


# --- AttributeValue --------------------------------------------------------------------


def desanidar(valor: dict) -> object:
    """Convierte un AttributeValue en un valor de Python.

    `{"N": "6"}` queda en `6` y `{"N": "1.5"}` en `1.5`; las listas y los mapas se resuelven
    hacia abajo. Un tipo que no conocemos queda en `None`.
    """
    if not isinstance(valor, dict):
        return None
    if "S" in valor:
        return valor["S"]
    if "N" in valor:
        texto = str(valor["N"])
        return float(texto) if "." in texto else int(texto)
    if "BOOL" in valor:
        return bool(valor["BOOL"])
    if "L" in valor:
        return [desanidar(elemento) for elemento in valor["L"]]
    if "M" in valor:
        return {clave: desanidar(dentro) for clave, dentro in valor["M"].items()}
    return None


def _plano(item: dict | None) -> dict:
    """Todos los atributos de un ítem, ya desanidados."""
    return {clave: desanidar(valor) for clave, valor in (item or {}).items()}


def _texto(datos: dict, clave: str) -> str | None:
    """El atributo como texto, o `None` si falta o viene vacío."""
    valor = datos.get(clave)
    return valor if isinstance(valor, str) and valor else None


def _nivel(valor: object) -> int | None:
    """El nivel si es un entero de 1 a 9; si no, `None`."""
    if isinstance(valor, bool) or not isinstance(valor, int):
        return None
    return valor if NIVEL_MINIMO <= valor <= NIVEL_MAXIMO else None


def _manifestaciones(datos: dict) -> list[dict]:
    return [m for m in (datos.get("manifestaciones") or []) if isinstance(m, dict)]


# --- criterios compartidos con el modo local -------------------------------------------


def clave_orden(texto: str) -> str:
    """Orden alfabético sin tildes ni mayúsculas ("Álvaro" queda junto a "Alba")."""
    plano = unicodedata.normalize("NFD", texto)
    return "".join(c for c in plano if not unicodedata.combining(c)).casefold()


def separar_nombre(nombre: str) -> tuple[str, str]:
    """Regla 2: "Martina M." -> ("Martina", "M."), la inicial distingue homónimos."""
    encontrado = _HOMONIMO.match(nombre.strip())
    return (encontrado.group(1), f"{encontrado.group(2)}.") if encontrado else (nombre.strip(), "")


def edad_meses(nacimiento: str, hoy: str) -> int:
    """Meses completos cumplidos (la misma fórmula de `lib/evaluacion.ts`)."""
    an, mn, dn = (int(x) for x in nacimiento[:10].split("-"))
    ah, mh, dh = (int(x) for x in hoy[:10].split("-"))
    meses = (ah - an) * 12 + (mh - mn) - (1 if dh < dn else 0)
    return max(0, meses)


def nivel_educativo(meses: int) -> str:
    """Regla 1: el nivel educativo de un tramo de edad en meses."""
    for tope, nivel in TRAMOS_NIVEL:
        if meses < tope:
            return nivel
    return NIVEL_MAS_ALTO


def mediana_baja(valores: list[int]) -> int:
    """La mediana baja: con dos al medio, la menor (igual que el generador local)."""
    ordenados = sorted(valores)
    return ordenados[(len(ordenados) - 1) // 2]


def nombre_sala(sala_grupo: str) -> str:
    """Regla 1: "SG-A" -> "Sala A"."""
    return f"Sala {sala_grupo.split('-')[-1]}"


def nombre_detectado(candidatos: object) -> str | None:
    """Regla 5: el nombre que se le muestra a la tía cuando la IA no identificó al niño.

    Es el primer candidato con puntaje suficiente. El umbral está en
    `UMBRAL_PUNTAJE_CANDIDATO` y es el único lugar que hay que tocar si se decide exigir
    más puntaje (ver DECISIÓN ABIERTA del spec).
    """
    for candidato in candidatos or []:
        if not isinstance(candidato, dict):
            continue
        puntaje = candidato.get("score")
        if isinstance(puntaje, bool) or not isinstance(puntaje, (int, float)):
            continue
        if puntaje < UMBRAL_PUNTAJE_CANDIDATO:
            continue
        return _texto(candidato, "nombre")
    return None


# --- jardín, salas y niños (reglas 1, 2 y 8) -------------------------------------------


def a_jardin(item: dict) -> Jardin:
    """Tabla Jardines -> `Jardin`."""
    datos = _plano(item)
    return Jardin(
        id=_texto(datos, "id_jardin") or "",
        nombre=_texto(datos, "nombre_fantasia") or "",
        comuna=_texto(datos, "comuna") or "",
        region=_texto(datos, "region") or "",
    )


def a_salas(item_jardin: dict, cfg: Config, ninos: list[Nino], hoy: str) -> list[Sala]:
    """Regla 1: las salas de `cfg.salas` que tiene el jardín, en ese orden.

    El nivel educativo sale de la mediana baja de la edad en meses de los niños de la sala
    a la fecha `hoy`. Una sala sin niños queda en el nivel más bajo.
    """
    datos = _plano(item_jardin)
    del_jardin = {s for s in (datos.get("salas") or []) if isinstance(s, str)}
    id_jardin = _texto(datos, "id_jardin") or cfg.jardin
    salas = []
    for sala_id in cfg.salas:
        if del_jardin and sala_id not in del_jardin:
            continue
        edades = [edad_meses(n.fechaNacimiento, hoy) for n in ninos if n.salaId == sala_id and n.fechaNacimiento]
        nivel: NivelEducativo = nivel_educativo(mediana_baja(edades)) if edades else NIVEL_SIN_NINOS  # type: ignore[assignment]
        salas.append(
            Sala(id=sala_id, jardinId=id_jardin, nombre=nombre_sala(sala_id), nivelEducativo=nivel)
        )
    return salas


def a_nino(item: dict) -> Nino:
    """Regla 2: tabla Ninos -> `Nino`. `ultimo_nivel` se ignora (regla 8)."""
    datos = _plano(item)
    nombre, inicial = separar_nombre(_texto(datos, "nombre") or "")
    return Nino(
        id=_texto(datos, "id_nino") or "",
        nombre=nombre,
        apellidoInicial=inicial,
        fechaNacimiento=_texto(datos, "fecha_nacimiento") or "",
        salaId=_texto(datos, "sala_grupo") or "",
        activo=True,
    )


def a_ninos(items: list[dict]) -> list[Nino]:
    """Regla 2: solo los que tienen nombre, ordenados por nombre y luego por inicial."""
    ninos = [a_nino(item) for item in items if _texto(_plano(item), "nombre")]
    ninos.sort(key=lambda n: (clave_orden(n.nombre), n.apellidoInicial))
    return ninos


# --- evidencias ------------------------------------------------------------------------


def _formato(valor: str | None) -> str:
    return valor if valor in FORMATOS else "texto"


def a_evidencia_captura(item: dict, estado: EstadoEvidencia) -> Evidencia:
    """Tabla propia Capturas -> `Evidencia`, con el estado que decidió la regla 6."""
    datos = _plano(item)
    return Evidencia(
        id=_texto(datos, "id_captura") or "",
        salaId=_texto(datos, "sala_grupo") or _texto(datos, "sala_id") or "",
        autorId=_texto(datos, "autor_id") or "",
        creadaEn=_texto(datos, "creada_en") or "",
        formato=_formato(_texto(datos, "formato")),  # type: ignore[arg-type]
        ninoIdSugerido=_texto(datos, "nino_id_sugerido"),
        textoExtraido=_texto(datos, "texto_extraido"),
        foto=None,
        estado=estado,
    )


def a_evidencia_registro(item: dict, estado: EstadoEvidencia) -> Evidencia:
    """Tabla Registros -> `Evidencia`: una nota de otra tía o de un script."""
    datos = _plano(item)
    tipo = _texto(datos, "tipo")
    formato = "audio" if tipo == "audio" else "foto" if tipo == "foto" else "texto"
    return Evidencia(
        id=_texto(datos, "id_captura") or "",
        salaId=_texto(datos, "sala_grupo") or "",
        autorId=_texto(datos, "id_educadora") or "",
        creadaEn=_texto(datos, "subido_en") or "",
        formato=formato,  # type: ignore[arg-type]
        textoExtraido=None,
        estado=estado,
    )


def _creada_en_historial(datos: dict) -> str:
    return f"{_texto(datos, 'fecha') or ''}T{HORA_HISTORIAL}{HUSO_HISTORIAL}"


def a_evidencia_historial(item: dict) -> Evidencia:
    """Regla 4: una observación del dataset vista como evidencia ya lista."""
    datos = _plano(item)
    return Evidencia(
        id=_texto(datos, "id_obs") or "",
        salaId=_texto(datos, "sala_grupo") or "",
        autorId=_texto(datos, "id_educadora") or "",
        creadaEn=_creada_en_historial(datos),
        formato="texto",
        textoExtraido=_texto(datos, "texto_literal"),
        estado="lista",
    )


def a_evidencia_observacion(item: dict) -> Evidencia:
    """Regla 5, último punto: captura de la app que no tiene fila en Capturas."""
    datos = _plano(item)
    archivo = _texto(datos, "archivo_s3") or ""
    return Evidencia(
        id=_texto(datos, "id_captura") or "",
        salaId=_texto(datos, "sala_grupo") or "",
        autorId=_texto(datos, "id_educadora") or "",
        creadaEn=_texto(datos, "creado_en") or _creada_en_historial(datos),
        formato="audio" if RUTA_AUDIO in archivo else "texto",
        textoExtraido=_texto(datos, "texto_literal"),
        estado="lista",
    )


# --- sugerencias (reglas 4 y 5) --------------------------------------------------------


def a_sugerencias_historial(item: dict) -> list[Sugerencia]:
    """Regla 4: una sugerencia aceptada por cada dominio distinto de la observación."""
    datos = _plano(item)
    id_obs = _texto(datos, "id_obs") or ""
    creada_en = _creada_en_historial(datos)
    autor = _texto(datos, "id_educadora")
    nivel_obs = _nivel(datos.get("nivel"))
    por_dominio: dict[str, list[dict]] = {}
    for manifestacion in _manifestaciones(datos):
        dominio = _texto(manifestacion, "dominio")
        if dominio in NUCLEOS:
            por_dominio.setdefault(dominio, []).append(manifestacion)
    sugerencias = []
    for dominio, del_dominio in por_dominio.items():
        niveles = [n for n in (_nivel(m.get("nivel")) for m in del_dominio) if n is not None]
        sugerencias.append(
            Sugerencia(
                id=f"{id_obs}{SEPARADOR_HISTORIAL}{dominio}",
                evidenciaId=id_obs,
                salaId=_texto(datos, "sala_grupo") or "",
                tipo="evaluacion",
                ninoId=_texto(datos, "id_nino"),
                nucleo=dominio,  # type: ignore[arg-type]
                nivel=nivel_obs if nivel_obs is not None else (max(niveles) if niveles else None),
                conducta=_texto(del_dominio[0], "texto_observable"),
                cita=" ".join(_texto(m, "texto_observable") or "" for m in del_dominio),
                certeza="alta",
                estado="aceptada",
                validadaPor=autor,
                validadaEn=creada_en,
            )
        )
    return sugerencias


def _manifestacion_elegida(manifestaciones: list[dict]) -> dict:
    """Regla 5: la de mayor certeza (alta, media, baja); ante empate, la primera."""
    if not manifestaciones:
        return {}
    return min(
        manifestaciones,
        key=lambda m: ORDEN_CERTEZA.get(_texto(m, "certeza") or "", CERTEZA_SIN_DATO),
    )


def _certeza(datos: dict, tipo_obs: str | None) -> str:
    certeza = _texto(datos, "certeza")
    if certeza in CERTEZAS:
        return certeza or ""
    return "alta" if tipo_obs == "GENERAL" else "baja"


def _motivo_sin_evaluar(datos: dict) -> str | None:
    """La conducta que explica por qué la IA no evaluó la nota, o `None` si sí la evaluó."""
    evaluabilidad = _texto(datos, "evaluabilidad")
    error = _texto(datos, "error_evaluacion")
    if evaluabilidad not in (None, "EVALUABLE"):
        return MOTIVOS_NO_EVALUABLE.get(_texto(datos, "motivo_no_evaluable") or "", CONDUCTA_SIN_EVALUAR)
    return CONDUCTA_SIN_EVALUAR if error else None


def a_sugerencia(item: dict) -> Sugerencia:
    """Regla 5: una observación de la app (`origen == "app"`) -> `Sugerencia` pendiente.

    Las decisiones guardadas las superpone después `datos/lectura.py` (regla 7).
    """
    datos = _plano(item)
    tipo_obs = _texto(datos, "tipo")
    nino_id = _texto(datos, "id_nino")
    elegida = _manifestacion_elegida(_manifestaciones(datos))
    sin_evaluar = _motivo_sin_evaluar(datos)
    nucleo = _texto(elegida, "dominio")
    nivel_obs = _nivel(datos.get("nivel"))
    return Sugerencia(
        id=_texto(datos, "id_obs") or "",
        evidenciaId=_texto(datos, "id_captura") or "",
        salaId=_texto(datos, "sala_grupo") or "",
        tipo="nota_sala" if tipo_obs == "GENERAL" else "evaluacion",
        ninoId=nino_id,
        nombreDetectado=None if nino_id else nombre_detectado(datos.get("candidatos")),
        nucleo=None if sin_evaluar else (nucleo if nucleo in NUCLEOS else None),  # type: ignore[arg-type]
        nivel=None if sin_evaluar else (nivel_obs if nivel_obs is not None else _nivel(elegida.get("nivel"))),
        conducta=sin_evaluar or _texto(elegida, "texto_observable"),
        cita=_texto(datos, "texto_literal") or "",
        certeza=_certeza(datos, tipo_obs),  # type: ignore[arg-type]
        estado="pendiente",
    )


# --- regla 6 ---------------------------------------------------------------------------


def estado_de_registro(estado: str | None) -> EstadoEvidencia:
    """Regla 6: el estado de la tabla Registros traducido al de la tía.

    Sin fila todavía, o con un valor que no conocemos, la nota sigue `procesando`.
    `SIN_TEXTO` es `error` porque para la tía significa "no pudimos leerla".
    """
    return ESTADOS_REGISTRO.get(estado or "", "procesando")


def regla6(fila: dict, registro: dict | None, momento: datetime, minutos_max: int) -> EstadoEvidencia:
    """Regla 6: el estado de una captura propia, en este orden.

    1. la tía la archivó; 2. ya tiene `estado_final`; 3. falló el envío; 4. sigue
    enviándose; 5. lo que diga Registros; 6. y si quedó en `procesando` más de
    `minutos_max` minutos, es `error`.
    """
    datos = _plano(fila)
    if datos.get("archivada") is True:
        return "lista"
    final = _texto(datos, "estado_final")
    if final in ESTADOS_FINALES:
        return final  # type: ignore[return-value]
    envio = _texto(datos, "estado_envio")
    if envio == "error_envio":
        return "error"
    if envio == "enviando":
        estado: EstadoEvidencia = "procesando"
    else:
        estado = estado_de_registro(_texto(_plano(registro), "estado"))
    if estado == "procesando":
        creada_en = _texto(datos, "creada_en") or ""
        if tiempo.minutos_desde(creada_en, momento) > minutos_max:
            return "error"
    return estado
