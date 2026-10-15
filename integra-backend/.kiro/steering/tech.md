---
inclusion: always
---
# Stack técnico (mínimo a propósito)

## Lenguaje
- **Python 3.13**. Dependencias: `boto3`, `pydantic>=2`, `jsonschema`, `rapidfuzz`. Dev: `pytest`, `ruff`.
- Similitud coseno en Python puro (≈90 vectores).

## AWS (región `us-east-1`, parametrizable) — SOLO estos recursos
| Recurso | Uso |
|---|---|
| **1 función Lambda** `ProcesarNota` | Todo el pipeline, síncrono. Timeout 300 s, 1024 MB. Se dispara por eventos S3 del bucket de capturas (prefijo `capturas/`, sufijos `meta.json` y `texto.json`); también admite `sam remote invoke` para pruebas. Sin API Gateway |
| **Amazon Bedrock Runtime** (Converse API) | Modelos disponibles en Bedrock: **Claude Haiku 4.5** para separar/identificar; **Claude Sonnet 5** para conductas y clasificación del código de manifestación |
| **Bedrock embeddings** (Titan Text Embeddings V2) | Embeber la rúbrica (una vez, por script) y cada consulta (en la Lambda) |
| **DynamoDB** (on-demand), 5 tablas | `Jardines`; `Educadoras` (GSI `porJardin`); `Ninos` (GSI `porJardin`, + `ultima_obs_fecha`/`ultimo_nivel`/`ultimo_nivel_fecha`); `Registros` (estado de cada captura, GSI `porSala`); `Observaciones` (resultados, GSI `porNino` y `porSala`) |
| **S3**, 2 buckets | **rubrica**: `rubrica/rubrica.json`, `rubrica/fewshot.json`, `rubrica/embeddings_rubrica.json`. **capturas** (nombre fijo con `!Sub` + AccountId): `capturas/{id_captura}/meta.json`, `capturas/{id_captura}/original/…`, `capturas/{id_captura}/texto.json` |
| **IAM** | Un rol para la Lambda con mínimo privilegio: lectura/escritura de las tablas, `s3:GetObject` en `rubrica/*` y `capturas/*`, `dynamodb:PutItem/UpdateItem` en `Registros`, `dynamodb:UpdateItem` en `Ninos`, Bedrock |
| **CloudWatch Logs** | Logs JSON sin PII |

Infraestructura como código: **AWS SAM** (`template.yaml`). No agregar otros servicios sin preguntar.

### Disparo por S3 e idempotencia
- Dos notificaciones S3 sobre `capturas/`: sufijo `meta.json` → **upsert** de la fila en `Registros` (estado `RECIBIDO`);
  sufijo `texto.json` → procesa. `meta.json` y `texto.json` pueden llegar en cualquier orden (todas las escrituras a `Registros` son upsert).
- `id_captura` sale de la ruta S3 (`capturas/<id>/...`), formato `CAP-<ULID>`, validado. `procesar_nota` lo **recibe** (no lo genera).
- `id_obs` deterministas: `{id_captura}-p{n_parte}-{n_obs}`. Así un reintento de S3 reprocesa y sobrescribe, sin duplicar.
- La educadora, la sala, la fecha de observación y el tipo vienen **solo de `meta.json`**, nunca de las partes de `texto.json`.
- Si falla una parte, las demás siguen: `Registros.estado = PROCESADO` con una lista `errores` por parte. `ERROR` es solo si
  falla todo o el error es de captura completa (`EDUCADORA_DESCONOCIDA`, `SALA_DESCONOCIDA`, `meta.json` ausente o inválido);
  en ese caso el código va en `Registros.error`.
- Fechas en ISO 8601; las horas con zona (`-03:00`). Claves compuestas: `sala_key = "{id_jardin}#{sala_grupo}"`,
  `orden = "{fecha}#{creado_en}"` (fecha de la observación, no la de subida).

## Reglas para el código que llama al LLM
- **Todas** las llamadas pasan por `src/core/llm.py::call_json(prompt_id, variables, schema, model_id, ...)`.
- Salida estructurada: *structured outputs* de Bedrock si el modelo/región lo soporta (consultar con el MCP `aws-docs`);
  si no, **tool use forzado** (`toolConfig` con un único tool cuyo `inputSchema.json` es el esquema y
  `toolChoice={"tool":{"name":...}}`). Validar SIEMPRE con `jsonschema` y luego pydantic.
- Prompts en `src/prompts/*.md` (secciones `## SYSTEM` / `## USER` con `{{variables}}`); esquemas en `src/schemas/*.json`.
  **No reescribirlos sin mostrar el diff y justificar.** Las claves `x-enum-from` / `x-range-from` de los esquemas se
  reemplazan en `llm.py` por `enum` / `minimum`-`maximum` tomados de la rúbrica cargada.
- IDs de modelo SOLO por variables de entorno: `MODEL_ID_SEPARAR`, `MODEL_ID_CONDUCTAS`, `MODEL_ID_EVALUAR`, `MODEL_ID_EMBEDDINGS`.
- Reintentos con backoff ante `ThrottlingException`/`ServiceUnavailableException`; 1 reintento si el JSON no valida.
- **Nunca hardcodear la cantidad de niveles ni de códigos** (ni 9 ni 8): todo sale de `rubrica.json`. El dataset E-1 tiene
  9 niveles; la rúbrica real de Integra tendrá 8 por nivel educativo y llegará como otro `rubrica.json`.
- Toda salida del LLM se valida en código (refs de nómina, frases literales, manifestaciones del nivel).
- Paralelismo con `ThreadPoolExecutor` (máx. 5): fragmentos en paralelo y corridas de evaluación en paralelo.

## Variables de entorno
`TABLA_JARDINES`, `TABLA_EDUCADORAS`, `TABLA_NINOS`, `TABLA_REGISTROS`, `TABLA_OBSERVACIONES`, `BUCKET` (rúbrica), `BUCKET_CAPTURAS`, `MODEL_ID_*`, `N_CORRIDAS_EVALUAR` (3), `TOP_K` (8), `LOG_LEVEL`.
En local, además `FUENTE_DATOS=local` (lee `data/processed/` en vez de S3/DynamoDB). Región: leer `AWS_REGION` y, si no existe, `AWS_DEFAULT_REGION` (default `us-east-1`).

## Credenciales
Credenciales **temporales** del evento como variables de entorno de la sesión de PowerShell (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_DEFAULT_REGION`). No usar `--profile`. El código usa la cadena estándar de boto3 (nunca leer ni escribir claves a mano). Antes de crear recursos, confirmar la cuenta con `aws sts get-caller-identity`; si falla con `ExpiredToken`, pedirme credenciales nuevas. Nunca claves en el repo ni en archivos versionados.

## Pruebas
- `tests/unit`: dominio puro sin AWS. `tests/llm` (`-m llm`): llaman a Bedrock, no corren por defecto.
- `scripts/pipeline_local.py`: corre el pipeline completo en el computador (Bedrock real, datos locales) e imprime el JSON.
