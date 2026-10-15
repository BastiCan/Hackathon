"""Pipeline sincrono: procesar_nota(entrada) -> Resultado.

Orquesta separar -> identificar -> (por particular) conductas -> recuperar ->
clasificar (N corridas) -> consolidar -> cruzar rubrica -> comparar edad.
Reglas de dominio en dominio.md; prompts en src/prompts; esquemas en src/schemas.
La edad NUNCA llega al LLM: se usa solo en codigo despues de evaluar (dominio.md Sec. 1).
"""

from __future__ import annotations

import json
import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date

from ulid import ULID

from . import capturas as capturas_mod
from . import edad as edad_mod
from . import nombres as nombres_mod
from . import validaciones as val
from .config import config
from .datos import Datos
from .llm import call_json, cargar_esquema
from .modelos import (
    Entrada,
    ErrorCaptura,
    ErrorEvaluacion,
    Evaluabilidad,
    MotivoNoEvaluable,
    Nino,
    Observacion,
    Resultado,
    Sugerencia,
    TipoObservacion,
)
from .postproceso import Corrida, CorridaCodigo, componer_comentario, consolidar
from .retriever import Retriever
from .rubrica import Rubrica

MAX_WORKERS = 5


class ErrorCapturaExc(Exception):
    """Error que rechaza la nota completa (TEXTO_VACIO, EDUCADORA/SALA_DESCONOCIDA)."""

    def __init__(self, codigo: ErrorCaptura, mensaje: str = "") -> None:
        super().__init__(mensaje or codigo.value)
        self.codigo = codigo


# --- Formato de las variables de los prompts (design.md) ---

def _formato_nomina(nomina: list[Nino]) -> tuple[str, dict[str, Nino]]:
    """`N1: Sofia M. - apodos: Sofi, la Sofi` por linea. Devuelve (texto, ref->Nino)."""
    lineas: list[str] = []
    refs: dict[str, Nino] = {}
    for i, nino in enumerate(nomina, 1):
        ref = f"N{i}"
        refs[ref] = nino
        if nino.apodos:
            lineas.append(f"{ref}: {nino.nombre} - apodos: {', '.join(nino.apodos)}")
        else:
            lineas.append(f"{ref}: {nino.nombre}")
    return "\n".join(lineas), refs


def _formato_niveles(rubrica: Rubrica) -> str:
    """`Nivel 8 - Combinacion...: <descripcion>` por linea. SIN rangos de edad."""
    return "\n".join(
        f"Nivel {n.nivel} - {n.nombre_nivel}: {n.descripcion}" for n in rubrica.niveles
    )


def _formato_candidatas(candidatas, barajar: bool = False) -> str:
    """`MAN-L08-LC-01 | lenguaje_comunicacion | <texto>` por linea."""
    items = list(candidatas)
    if barajar:
        random.shuffle(items)
    return "\n".join(
        f"{c.id_manifestacion} | {c.dominio} | {c.texto_observable}" for c in items
    )


def _formato_conductas(conductas: list[dict]) -> str:
    return json.dumps(conductas, ensure_ascii=False)


def _formato_ejemplos(fewshot: dict) -> str:
    """Arma {{ejemplos}} desde fewshot.json._formato (Protagonista/Observacion/Respuesta)."""
    bloques: list[str] = []
    for ej in fewshot["ejemplos"]:
        respuesta = json.dumps(ej["respuesta"], ensure_ascii=False)
        bloques.append(
            f"Protagonista: {ej['protagonista']}\n"
            f'Observacion: "{ej["nota"]}"\n'
            f"Respuesta: {respuesta}"
        )
    return "\n\n".join(bloques)


# --- Contexto de ejecucion ---

@dataclass
class Contexto:
    rubrica: Rubrica
    retriever: Retriever
    fewshot: dict
    datos: Datos
    schema_separar: dict
    schema_conductas: dict
    schema_clasificar: dict
    niveles_desc: str
    ejemplos: str


def _ulid() -> str:
    return str(ULID())


# --- Separar e identificar ---

def _resolver_sujeto(nombre: str, nomina: list[Nino], resto: list[Nino]) -> nombres_mod.Resolucion:
    return nombres_mod.resolver(nombre, nomina, resto)


# --- Evaluacion de una observacion particular identificada ---

def _extraer_conductas(ctx: Contexto, texto: str, protagonista: str) -> tuple[dict, object]:
    return call_json(
        prompt_id="extraer_conductas",
        variables={"protagonista": protagonista, "texto": texto},
        schema=ctx.schema_conductas,
        model_id=config.model_id_conductas,
        temperature=0,
        rubrica=ctx.rubrica,
    )


def _una_corrida_clasificar(ctx: Contexto, texto: str, protagonista: str, conductas: list[dict], candidatas) -> Corrida:
    datos, _ = call_json(
        prompt_id="clasificar",
        variables={
            "niveles_descripcion": ctx.niveles_desc,
            "protagonista": protagonista,
            "texto": texto,
            "conductas_json": _formato_conductas(conductas),
            "candidatas": _formato_candidatas(candidatas, barajar=True),
            "ejemplos": ctx.ejemplos,
        },
        schema=ctx.schema_clasificar,
        model_id=config.model_id_evaluar,
        temperature=0.4,
        rubrica=ctx.rubrica,
    )
    codigos = [
        CorridaCodigo(id_manifestacion=m["id_manifestacion"], frase_evidencia=m["frase_evidencia"])
        for m in datos.get("manifestaciones", [])
    ]
    return Corrida(
        codigos=codigos,
        otro_codigo_viable=datos.get("otro_codigo_viable"),
        comentario=datos.get("comentario", ""),
    )


def _recuperar_candidatas(ctx: Contexto, conductas: list[dict]):
    """Por cada conducta embebe su `accion`, une resultados y recorta a 2*TOP_K."""
    vistos: dict[str, object] = {}
    for c in conductas:
        accion = c.get("accion", "")
        if not accion:
            continue
        for cand in ctx.retriever.buscar(accion, k=config.top_k):
            if cand.id_manifestacion not in vistos:
                vistos[cand.id_manifestacion] = cand
    candidatas = list(vistos.values())
    return candidatas[: 2 * config.top_k]


def _evaluar_particular(
    ctx: Contexto, obs: Observacion, protagonista: str, nino: Nino, fecha_nota: date
) -> Observacion:
    """Conductas -> (si evaluable) recuperar -> clasificar N -> consolidar -> edad."""
    try:
        conductas_json, _ = _extraer_conductas(ctx, obs.texto_literal, protagonista)
    except Exception:  # noqa: BLE001 - salida LLM invalida tras reintento
        obs.error_evaluacion = ErrorEvaluacion.LLM_SALIDA_INVALIDA
        return obs

    conductas = conductas_json.get("conductas", [])
    obs.conductas = _conductas_a_modelo(conductas)

    if not conductas_json.get("evaluable", False):
        obs.evaluabilidad = Evaluabilidad.NO_EVALUABLE
        motivo = conductas_json.get("motivo_no_evaluable")
        obs.motivo_no_evaluable = MotivoNoEvaluable(motivo) if motivo else MotivoNoEvaluable.OTRO
        obs.nivel = None
        _agregar_nota_edad(obs, nino, fecha_nota, base_comentario="")
        return obs

    obs.evaluabilidad = Evaluabilidad.EVALUABLE

    candidatas = _recuperar_candidatas(ctx, conductas)
    if not candidatas:
        obs.nivel = None
        obs.comentario = componer_comentario("Sin manifestaciones candidatas.", [], "")
        _agregar_nota_edad(obs, nino, fecha_nota, base_comentario=obs.comentario)
        return obs

    # N corridas en paralelo, candidatas barajadas en cada una.
    corridas = _correr_clasificaciones(ctx, obs.texto_literal, protagonista, conductas, candidatas)
    consolidado = consolidar(corridas)

    # Validar y cruzar cada codigo con la rubrica (frase literal + codigo valido).
    sugerencias: list[Sugerencia] = []
    for cc in consolidado.codigos:
        if not ctx.rubrica.existe(cc.id_manifestacion):
            continue
        if not val.frase_evidencia_valida(cc.frase_evidencia, obs.texto_literal):
            continue
        cruce = ctx.rubrica.cruzar(cc.id_manifestacion)
        sugerencias.append(
            Sugerencia(
                id_manifestacion=cc.id_manifestacion,
                nivel=cruce.nivel,
                dominio=cruce.dominio,
                texto_observable=cruce.texto_observable,
                frase_evidencia=cc.frase_evidencia,
                certeza=cc.certeza,
            )
        )

    obs.manifestaciones = sugerencias
    if not sugerencias:
        obs.nivel = None
        obs.certeza = None
    else:
        principal = max(sugerencias, key=lambda s: _rango_certeza(s.certeza))
        obs.nivel = principal.nivel
        obs.certeza = principal.certeza

    base = componer_comentario(consolidado.comentario, consolidado.alternativas, "")
    _agregar_nota_edad(obs, nino, fecha_nota, base_comentario=base)
    return obs


def _correr_clasificaciones(ctx, texto, protagonista, conductas, candidatas) -> list[Corrida]:
    n = config.n_corridas_evaluar
    corridas: list[Corrida] = []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, n)) as ex:
        futuros = [
            ex.submit(_una_corrida_clasificar, ctx, texto, protagonista, conductas, candidatas)
            for _ in range(n)
        ]
        for fut in futuros:
            try:
                corridas.append(fut.result())
            except Exception:  # noqa: BLE001, S112 - una corrida invalida no tumba el resto
                continue
    return corridas


def _rango_certeza(certeza) -> int:
    from .modelos import Certeza

    return {Certeza.ALTA: 3, Certeza.MEDIA: 2, Certeza.BAJA: 1}.get(certeza, 0)


def _conductas_a_modelo(conductas: list[dict]):
    from .modelos import Conducta

    salida = []
    for c in conductas:
        try:
            salida.append(Conducta(**c))
        except Exception:  # noqa: BLE001, S112 - si el LLM manda algo raro, se omite esa conducta
            continue
    return salida


def _agregar_nota_edad(obs: Observacion, nino: Nino, fecha_nota: date, base_comentario: str) -> None:
    """Calcula edad (solo codigo), compara con lo esperado y agrega una frase al comentario."""
    edad = edad_mod.edad_meses(nino.fecha_nacimiento, fecha_nota)
    obs.edad_meses = edad
    # Se necesita la rubrica para los rangos; se obtiene via el modulo de edad con la rubrica global.
    esperados, fuera = _niveles_esperados_cache(edad)
    obs.niveles_esperados = esperados
    obs.fuera_de_rango_rubrica = fuera

    nota = ""
    if obs.nivel is not None and esperados:
        comp = edad_mod.comparar(obs.nivel, esperados)
        obs.comparacion_edad = comp
        esp_txt = esperados[0] if len(esperados) == 1 else f"{esperados[0]} o {esperados[-1]}"
        nota = (
            f"Para su edad ({edad} meses) lo esperado es el nivel {esp_txt}; "
            f"esta observacion muestra una conducta de nivel {obs.nivel}."
        )
        if fuera:
            nota += " (La edad supera el rango de la rubrica.)"
    obs.comentario = componer_comentario(base_comentario, [], nota)


# Cache del Retriever/Rubrica para la nota de edad (se setea en procesar_nota).
_rubrica_actual: Rubrica | None = None


def _niveles_esperados_cache(edad: int) -> tuple[list[int], bool]:
    assert _rubrica_actual is not None
    return edad_mod.niveles_esperados(edad, _rubrica_actual)


# --- Reutilizable por medir.py (clasificacion sola, protagonista conocido) ---

def construir_contexto(datos: Datos, rubrica: Rubrica, retriever: Retriever, fewshot: dict) -> Contexto:
    """Arma el Contexto del pipeline (esquemas + strings precomputados)."""
    return Contexto(
        rubrica=rubrica,
        retriever=retriever,
        fewshot=fewshot,
        datos=datos,
        schema_separar=cargar_esquema("separar_identificar"),
        schema_conductas=cargar_esquema("extraer_conductas"),
        schema_clasificar=cargar_esquema("clasificar"),
        niveles_desc=_formato_niveles(rubrica),
        ejemplos=_formato_ejemplos(fewshot),
    )


@dataclass
class ResultadoClasificacion:
    """Salida de clasificar_texto: lo que medir.py necesita (sin identificar/edad)."""

    evaluable: bool
    motivo_no_evaluable: str | None
    conductas: list[dict]
    sugerencias: list[Sugerencia]
    nivel: int | None
    certeza: object | None


def clasificar_texto(ctx: Contexto, texto: str, protagonista: str) -> ResultadoClasificacion:
    """Conductas -> recuperar -> N corridas -> consolidar -> cruzar. Sin identificar ni edad.

    Usado por scripts/medir.py (protagonista conocido). Reusa los helpers del pipeline.
    """
    conductas_json, _ = _extraer_conductas(ctx, texto, protagonista)
    conductas = conductas_json.get("conductas", [])

    if not conductas_json.get("evaluable", False):
        return ResultadoClasificacion(
            evaluable=False,
            motivo_no_evaluable=conductas_json.get("motivo_no_evaluable"),
            conductas=conductas,
            sugerencias=[],
            nivel=None,
            certeza=None,
        )

    candidatas = _recuperar_candidatas(ctx, conductas)
    if not candidatas:
        return ResultadoClasificacion(True, None, conductas, [], None, None)

    corridas = _correr_clasificaciones(ctx, texto, protagonista, conductas, candidatas)
    consolidado = consolidar(corridas)

    sugerencias: list[Sugerencia] = []
    for cc in consolidado.codigos:
        if not ctx.rubrica.existe(cc.id_manifestacion):
            continue
        if not val.frase_evidencia_valida(cc.frase_evidencia, texto):
            continue
        cruce = ctx.rubrica.cruzar(cc.id_manifestacion)
        sugerencias.append(
            Sugerencia(
                id_manifestacion=cc.id_manifestacion,
                nivel=cruce.nivel,
                dominio=cruce.dominio,
                texto_observable=cruce.texto_observable,
                frase_evidencia=cc.frase_evidencia,
                certeza=cc.certeza,
            )
        )

    if sugerencias:
        principal = max(sugerencias, key=lambda s: _rango_certeza(s.certeza))
        nivel, certeza = principal.nivel, principal.certeza
    else:
        nivel, certeza = None, None
    return ResultadoClasificacion(True, None, conductas, sugerencias, nivel, certeza)


# --- Entrada principal ---

def procesar_nota(
    entrada: Entrada,
    datos: Datos,
    rubrica: Rubrica,
    retriever: Retriever,
    fewshot: dict,
    *,
    id_captura: str | None = None,
    n_parte: int = 0,
    archivo_s3: str | None = None,
) -> Resultado:
    """Procesa una nota (una parte de la captura) y devuelve el Resultado.

    - `id_captura`: viene de la ruta S3; si es None (pruebas directas) se genera.
    - `n_parte`: indice de la parte dentro de la captura (para IDs deterministas).
    - `archivo_s3`: clave S3 del archivo original de esta parte; se copia a cada observacion.
    Guarda las observaciones y actualiza `Ninos`.
    """
    global _rubrica_actual
    _rubrica_actual = rubrica

    if id_captura is None:
        id_captura = f"CAP-{_ulid()}"

    # 1. Validar entrada.
    if not entrada.texto or entrada.texto.strip() == "":
        raise ErrorCapturaExc(ErrorCaptura.TEXTO_VACIO)
    educadora = datos.educadora(entrada.id_educadora)
    if educadora is None:
        raise ErrorCapturaExc(ErrorCaptura.EDUCADORA_DESCONOCIDA)

    # 2. Contexto: ninos del jardin, filtrar por fecha_ingreso, separar nomina/resto.
    ninos_jardin = [
        n for n in datos.ninos_de_jardin(educadora.id_jardin) if n.fecha_ingreso <= entrada.fecha
    ]
    nomina = [n for n in ninos_jardin if n.sala_grupo == entrada.sala_grupo]
    resto = [n for n in ninos_jardin if n.sala_grupo != entrada.sala_grupo]
    if not nomina:
        raise ErrorCapturaExc(ErrorCaptura.SALA_DESCONOCIDA)

    ctx = Contexto(
        rubrica=rubrica,
        retriever=retriever,
        fewshot=fewshot,
        datos=datos,
        schema_separar=cargar_esquema("separar_identificar"),
        schema_conductas=cargar_esquema("extraer_conductas"),
        schema_clasificar=cargar_esquema("clasificar"),
        niveles_desc=_formato_niveles(rubrica),
        ejemplos=_formato_ejemplos(fewshot),
    )

    advertencias: list[str] = []
    # Contador de observaciones para IDs deterministas dentro de esta parte.
    contador = [0]

    # 3. Separar e identificar.
    texto_nomina, _refs = _formato_nomina(nomina)
    separado, _ = call_json(
        prompt_id="separar_identificar",
        variables={
            "fecha": entrada.fecha.isoformat(),
            "nomina": texto_nomina,
            "texto": entrada.texto,
        },
        schema=ctx.schema_separar,
        model_id=config.model_id_separar,
        temperature=0,
        rubrica=rubrica,
    )

    fragmentos = separado.get("fragmentos", [])
    # Cobertura: advertir si queda texto sustantivo sin asignar.
    textos_frag = [f["texto_literal"] for f in fragmentos]
    if val.texto_no_cubierto(entrada.texto, textos_frag):
        advertencias.append(val.ADVERTENCIA_TEXTO_NO_CUBIERTO)

    observaciones: list[Observacion] = []
    for frag in fragmentos:
        observaciones.extend(
            _procesar_fragmento(
                ctx, frag, nomina, resto, entrada.fecha, id_captura, n_parte, contador, archivo_s3
            )
        )

    resultado = Resultado(id_captura=id_captura, advertencias=advertencias, observaciones=observaciones)
    cabecera = {
        "fecha": entrada.fecha.isoformat(),
        "id_educadora": entrada.id_educadora,
        "id_jardin": educadora.id_jardin,
        "sala_grupo": entrada.sala_grupo,
    }
    datos.guardar_observaciones(observaciones, id_captura=id_captura, cabecera=cabecera)
    return resultado


def _procesar_fragmento(
    ctx: Contexto,
    frag: dict,
    nomina: list[Nino],
    resto: list[Nino],
    fecha_nota: date,
    id_captura: str,
    n_parte: int,
    contador: list[int],
    archivo_s3: str | None,
) -> list[Observacion]:
    texto = frag["texto_literal"]
    fecha_en_texto = frag.get("fecha_en_texto")

    def nuevo_id() -> str:
        oid = capturas_mod.id_obs(id_captura, n_parte, contador[0])
        contador[0] += 1
        return oid

    if frag.get("tipo") == "GENERAL":
        return [
            Observacion(
                id_obs=nuevo_id(),
                tipo=TipoObservacion.GENERAL,
                texto_literal=texto,
                fecha_en_texto=fecha_en_texto,
                archivo_s3=archivo_s3,
            )
        ]

    sujetos = frag.get("sujetos", [])
    if not sujetos:
        # PARTICULAR sin sujetos resolubles: se trata como no identificado.
        return [
            Observacion(
                id_obs=nuevo_id(),
                tipo=TipoObservacion.NO_IDENTIFICADO,
                texto_literal=texto,
                error_identificacion=nombres_mod.ErrorIdentificacion.NO_ENCONTRADO,
                fecha_en_texto=fecha_en_texto,
                archivo_s3=archivo_s3,
            )
        ]

    salida: list[Observacion] = []
    for sujeto in sujetos:
        nombre = sujeto.get("nombre_como_aparece", "")
        resol = _resolver_sujeto(nombre, nomina, resto)
        if resol.resuelto:
            nino = next(n for n in nomina if n.id_nino == resol.id_nino)
            obs = Observacion(
                id_obs=nuevo_id(),
                tipo=TipoObservacion.PARTICULAR,
                texto_literal=texto,
                id_nino=nino.id_nino,
                fecha_en_texto=fecha_en_texto,
                archivo_s3=archivo_s3,
            )
            obs = _evaluar_particular(ctx, obs, nombre, nino, fecha_nota)
            salida.append(obs)
        else:
            salida.append(
                Observacion(
                    id_obs=nuevo_id(),
                    tipo=TipoObservacion.NO_IDENTIFICADO,
                    texto_literal=texto,
                    error_identificacion=resol.error,
                    candidatos=list(resol.candidatos),
                    fecha_en_texto=fecha_en_texto,
                    archivo_s3=archivo_s3,
                )
            )
    return salida
