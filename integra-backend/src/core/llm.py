"""Llamadas al LLM (Bedrock Converse) con salida estructurada validada.

TODAS las llamadas al modelo pasan por `call_json` (tech.md). Se usa *tool use forzado*
(toolConfig con un unico tool cuyo inputSchema.json es el esquema, y toolChoice fijado a
ese tool): es la via soportada por los modelos Claude en Bedrock para obtener JSON. La
salida se valida SIEMPRE con jsonschema (y, si se pasa, con un modelo pydantic). Las
claves x-enum-from / x-range-from del esquema se resuelven contra la rubrica (rubrica.py).

Reintentos:
- Backoff exponencial ante ThrottlingException / ServiceUnavailableException (max 4 intentos).
- 1 reintento si el JSON devuelto no valida (se reitera avisando el error).

No se escribe el texto de las notas en logs (requirements 5): el logging queda a cargo
de quien llama; aqui solo se devuelven metadatos (LlmMeta) sin PII.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from jsonschema import Draft202012Validator
from pydantic import BaseModel

from .config import RAIZ, config
from .rubrica import Rubrica, cargar_rubrica, resolver_esquema

PROMPTS_DIR = RAIZ / "src" / "prompts"
SCHEMAS_DIR = RAIZ / "src" / "schemas"

MAX_INTENTOS_THROTTLE = 4
_ERRORES_REINTENTABLES = {"ThrottlingException", "ServiceUnavailableException"}
_TOOL_NAME = "entregar_json"


class LlmError(RuntimeError):
    """Error no recuperable al llamar al LLM (p. ej. salida invalida tras reintento)."""


@dataclass(frozen=True)
class LlmMeta:
    """Metadatos de una llamada (sin PII)."""

    prompt_id: str
    prompt_version: str
    model_id: str
    intentos: int
    tokens_entrada: int
    tokens_salida: int
    latencia_ms: int


# --- Prompts ---

_SECCION_RE = re.compile(r"^##\s+(SYSTEM|USER)\s*$", re.MULTILINE)


def _version_prompt(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]


def cargar_prompt(prompt_id: str) -> tuple[str, str, str]:
    """Lee src/prompts/<id>.md y devuelve (system, user, version).

    El archivo tiene secciones `## SYSTEM` y `## USER`. La version es un hash corto
    del contenido completo (para trazar que prompt se uso sin versionar a mano).
    """
    ruta = PROMPTS_DIR / f"{prompt_id}.md"
    texto = ruta.read_text(encoding="utf-8")
    version = _version_prompt(texto)

    partes = _SECCION_RE.split(texto)
    # partes = [preludio, 'SYSTEM', cuerpo_system, 'USER', cuerpo_user, ...]
    secciones: dict[str, str] = {}
    for i in range(1, len(partes) - 1, 2):
        secciones[partes[i].upper()] = partes[i + 1].strip()

    if "SYSTEM" not in secciones or "USER" not in secciones:
        raise LlmError(f"prompt {prompt_id} debe tener secciones ## SYSTEM y ## USER")
    return secciones["SYSTEM"], secciones["USER"], version


def _sustituir(plantilla: str, variables: dict[str, Any]) -> str:
    """Reemplaza {{clave}} por su valor (str). No falla si sobran variables."""
    def repl(m: re.Match[str]) -> str:
        clave = m.group(1).strip()
        if clave not in variables:
            raise LlmError(f"falta la variable de prompt: {clave}")
        return str(variables[clave])

    return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", repl, plantilla)


# --- Esquemas ---

def cargar_esquema(nombre: str) -> dict[str, Any]:
    """Lee src/schemas/<nombre>.json (sin resolver x-enum-from)."""
    ruta = SCHEMAS_DIR / f"{nombre}.json"
    return json.loads(ruta.read_text(encoding="utf-8"))


# --- Cliente Bedrock (perezoso) ---

_cliente = None


def _bedrock():
    global _cliente
    if _cliente is None:
        _cliente = boto3.client(
            "bedrock-runtime",
            region_name=config.region,
            config=BotoConfig(retries={"max_attempts": 0, "mode": "standard"}),
        )
    return _cliente


def _tool_config(esquema: dict[str, Any]) -> dict[str, Any]:
    return {
        "tools": [
            {
                "toolSpec": {
                    "name": _TOOL_NAME,
                    "description": "Devuelve la respuesta en el formato JSON requerido.",
                    "inputSchema": {"json": esquema},
                }
            }
        ],
        "toolChoice": {"tool": {"name": _TOOL_NAME}},
    }


def _extraer_tool_input(respuesta: dict[str, Any]) -> dict[str, Any] | None:
    """Saca el input del bloque toolUse de la respuesta Converse, si existe."""
    contenido = respuesta.get("output", {}).get("message", {}).get("content", [])
    for bloque in contenido:
        if "toolUse" in bloque and bloque["toolUse"].get("name") == _TOOL_NAME:
            return bloque["toolUse"].get("input")
    return None


def _converse(
    model_id: str,
    system: str,
    mensajes: list[dict[str, Any]],
    esquema: dict[str, Any],
    temperature: float | None,
    max_tokens: int,
) -> dict[str, Any]:
    """Una llamada Converse con tool use forzado, con backoff ante throttling."""
    inference: dict[str, Any] = {"maxTokens": max_tokens}
    if temperature is not None:
        inference["temperature"] = temperature

    espera = 1.0
    ultimo_error: Exception | None = None
    for intento in range(1, MAX_INTENTOS_THROTTLE + 1):
        try:
            return _bedrock().converse(
                modelId=model_id,
                system=[{"text": system}],
                messages=mensajes,
                inferenceConfig=inference,
                toolConfig=_tool_config(esquema),
            )
        except Exception as e:
            nombre = type(e).__name__
            codigo = getattr(e, "response", {}).get("Error", {}).get("Code", "") if hasattr(e, "response") else ""
            if nombre in _ERRORES_REINTENTABLES or codigo in _ERRORES_REINTENTABLES:
                ultimo_error = e
                if intento < MAX_INTENTOS_THROTTLE:
                    time.sleep(espera)
                    espera *= 2
                    continue
            raise
    raise LlmError(f"throttling persistente tras {MAX_INTENTOS_THROTTLE} intentos") from ultimo_error


def call_json(
    prompt_id: str,
    variables: dict[str, Any],
    schema: dict[str, Any],
    model_id: str,
    temperature: float | None = None,
    max_tokens: int = 2000,
    *,
    rubrica: Rubrica | None = None,
    modelo_pydantic: type[BaseModel] | None = None,
) -> tuple[dict[str, Any], LlmMeta]:
    """Llama al LLM y devuelve (json_validado, LlmMeta).

    - `schema`: JSON Schema de salida (puede traer x-enum-from / x-range-from).
    - `rubrica`: para resolver esos x-*-from; si no se pasa, se carga la local.
    - `modelo_pydantic`: si se pasa, valida ademas con ese modelo.
    Lanza LlmError si el JSON no valida tras 1 reintento.
    """
    rub = rubrica if rubrica is not None else cargar_rubrica()
    esquema = resolver_esquema(schema, rub)
    validador = Draft202012Validator(esquema)

    system, plantilla_user, version = cargar_prompt(prompt_id)
    user = _sustituir(plantilla_user, variables)

    mensajes: list[dict[str, Any]] = [{"role": "user", "content": [{"text": user}]}]

    t0 = time.monotonic()
    tokens_in = tokens_out = 0
    datos: dict[str, Any] | None = None
    errores_validacion: list[str] = []

    # Hasta 2 pasadas: la segunda reitera avisando el error de validacion.
    for pasada in range(2):
        respuesta = _converse(model_id, system, mensajes, esquema, temperature, max_tokens)
        uso = respuesta.get("usage", {})
        tokens_in += uso.get("inputTokens", 0)
        tokens_out += uso.get("outputTokens", 0)

        candidato = _extraer_tool_input(respuesta)
        if candidato is not None:
            errores = sorted(validador.iter_errors(candidato), key=str)
            if not errores:
                datos = candidato
                break
            errores_validacion = [e.message for e in errores]
        else:
            errores_validacion = ["el modelo no devolvio el tool esperado"]

        if pasada == 0:
            # Reiterar: adjuntar la salida y el error para que el modelo corrija.
            mensajes.append(
                {"role": "assistant", "content": [{"text": json.dumps(candidato, ensure_ascii=False)}]}
            )
            mensajes.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "text": "La respuesta anterior no cumple el esquema: "
                            + "; ".join(errores_validacion)
                            + ". Devuelve de nuevo SOLO el tool con un JSON valido."
                        }
                    ],
                }
            )

    latencia_ms = int((time.monotonic() - t0) * 1000)

    if datos is None:
        raise LlmError(
            f"salida invalida de {prompt_id} tras reintento: {'; '.join(errores_validacion)}"
        )

    if modelo_pydantic is not None:
        modelo_pydantic.model_validate(datos)

    meta = LlmMeta(
        prompt_id=prompt_id,
        prompt_version=version,
        model_id=model_id,
        intentos=pasada + 1,
        tokens_entrada=tokens_in,
        tokens_salida=tokens_out,
        latencia_ms=latencia_ms,
    )
    return datos, meta
