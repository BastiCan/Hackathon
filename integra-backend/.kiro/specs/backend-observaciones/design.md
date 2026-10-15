# Design Document — Procesador de notas de sala

## Overview
Una sola Lambda síncrona. Recibe la nota, ejecuta el pipeline (1 llamada para separar + por cada observación particular:
1 para conductas y N para clasificar el código de manifestación), guarda en DynamoDB y devuelve el resultado. Reglas de dominio en
`.kiro/steering/dominio.md`; prompts en `src/prompts/`; esquemas en `src/schemas/`.

```mermaid
flowchart LR
  EV[Evento de prueba / sam remote invoke] --> L[λ ProcesarNota]
  L -->|GetItem / Query| DE[(DynamoDB Educadoras / Ninos)]
  L -->|GetObject al iniciar| S3[(S3 rubrica/)]
  L -->|Converse| BR[Bedrock · Claude]
  L -->|InvokeModel embeddings| BE[Bedrock · Titan V2]
  L -->|PutItem| DO[(DynamoDB Observaciones)]
```

## Flujo de `pipeline.procesar_nota(entrada)`
1. **Validar entrada** → errores de captura (`TEXTO_VACIO`, `EDUCADORA_DESCONOCIDA`, `SALA_DESCONOCIDA`).
2. **Contexto**: educadora → `id_jardin`; `Query Ninos` por `id_jardin`; filtrar `fecha_ingreso <= fecha`; separar
   `nomina` (sala pedida) y `resto_jardin`.
3. **Separar e identificar** (prompt `separar_identificar`, `MODEL_ID_SEPARAR`): nómina como `N1: Sofía M. — apodos: Sofi, la Sofi`.
   Validaciones: literal, cobertura, refs ∈ nómina, `nombres.resolver` confirma cada sujeto → `PARTICULAR` o `NO_IDENTIFICADO`;
   N sujetos → N observaciones.
4. Por cada particular identificada, en paralelo:
   a. **Conductas** (prompt `extraer_conductas`, `MODEL_ID_CONDUCTAS`) → si no evaluable, guardar y terminar.
   b. **Recuperar**: embeber cada `accion`, coseno contra las 90 manifestaciones (sin filtro de nivel), unir y recortar a `2*TOP_K`.
   c. **Clasificar** (prompt `clasificar`, `MODEL_ID_EVALUAR`) `N_CORRIDAS_EVALUAR` veces en paralelo, barajando candidatas.
      El prompt recibe las descripciones de los 9 niveles y los 9 ejemplos de `fewshot.json`. Devuelve SOLO códigos.
   d. **Cruzar y consolidar** (`postproceso.py`, sin IA): cada código → nivel, dominio, texto_observable desde `rubrica.json`;
      votación entre corridas → certeza y comentario (dominio.md §5).
   e. **Comparar con la edad** (`edad.py`, solo código): edad_meses, niveles_esperados, comparacion_edad; se agrega una frase al comentario.
5. **Guardar** todas las observaciones (GENERAL, PARTICULAR, NO_IDENTIFICADO) con `BatchWriteItem` y devolver.

## Componentes
```python
# edad.py  (solo código; el LLM nunca ve la edad)
def edad_meses(fecha_nac: date, f: date) -> int                         # fórmula del diccionario, >= 0
def niveles_esperados(edad: int, rubrica) -> tuple[list[int], bool]     # (niveles, fuera_de_rango_rubrica)
def comparar(nivel: int, esperados: list[int]) -> str                   # BAJO_LO_ESPERADO | ACORDE | SOBRE_LO_ESPERADO

# nombres.py  (rapidfuzz WRatio sobre nombre + apodos normalizados; match >= 88;
#              AMBIGUO si dos >= 88 o diferencia entre los dos mejores < 5)
def resolver(nombre_en_texto: str, nomina, resto_jardin) -> Resolucion

# llm.py
def call_json(prompt_id, variables, schema, model_id, temperature=None, max_tokens=2000) -> tuple[dict, LlmMeta]

# retriever.py
class Retriever:  # carga rubrica.json + embeddings_rubrica.json (S3 o local)
# rubrica.py: cruce código → {nivel, dominio, texto_observable} desde rubrica.json (diccionario, sin IA)
    def buscar(self, consulta: str, k: int) -> list[Candidata]   # sobre las 90, sin filtro

# datos.py  (dos implementaciones con la misma interfaz: DynamoDB y local con data/processed/)
def educadora(id) -> Educadora | None
def ninos_de_jardin(id_jardin) -> list[Nino]
def guardar_observaciones(lista: list[Observacion]) -> None

# handler.py
def handler(event, context) -> dict   # acepta el evento directo o {"body": "<json>"}
```

## Datos

### DynamoDB (on-demand)
| Tabla | PK | SK | Atributos |
|---|---|---|---|
| `Educadoras` | `id_educadora` | — | id_jardin, rol |
| `Ninos` | `id_jardin` | `id_nino` | sala_grupo, nombre, apodos[], fecha_nacimiento, fecha_ingreso |
| `Observaciones` | `id_captura` | `id_obs` | fecha, id_educadora, id_jardin, sala_grupo, tipo, texto_literal, id_nino, error_identificacion, candidatos[], evaluabilidad, motivo_no_evaluable, conductas[], sugerencias[], edad_meses, error_evaluacion, estado, llm_meta[], creado_en |

### S3 (1 bucket, acceso público bloqueado)
`rubrica/rubrica.json`, `rubrica/fewshot.json`, `rubrica/embeddings_rubrica.json`, `raw/` (dataset original).

`rubrica.json` (ya generado en `data/processed/`; NO regenerar):
```json
{"version":"E1-2026-10-13","dominios":[...],
 "niveles":[{"nivel":1,"nombre_nivel":"...","edad_min_meses":0,"edad_max_meses":2,"descripcion":"..."}],
 "manifestaciones":{"MAN-L01-CO-01":{"nivel":1,"dominio":"cognitivo","texto_observable":"..."}, ...}}
```
`fewshot.json` (ya generado): 9 ejemplos `{protagonista, nota, respuesta}` donde `respuesta` cumple exactamente el esquema
`clasificar.json` (`manifestaciones`, `otro_codigo_viable`, `comentario`, `sin_correspondencia`). Se insertan en `{{ejemplos}}`
con el formato de `fewshot.json._formato` (Protagonista / Observación / Respuesta en JSON compacto). En los 9 ejemplos
`otro_codigo_viable` es null a propósito: cualquier código alternativo sería de la validación y la contaminaría.
Embeddings: se embebe `"<dominio>: <texto_observable>"` de cada código (sin el número de nivel, para no sesgar).

### Nombres de demo (ya escritos, no generar otros)
El dataset está anonimizado (solo IDs). Para probar la identificación con datos reales, `tests/fixtures/nomina_demo.json`
asigna nombres y apodos a los 26 niños/as REALES de JAR-0001 (salas SG-A y SG-B, con sus IDs, fechas y salas del dataset).
Incluye a propósito una variante de escritura (Nayara/"Naiara"), dos "Martina" en SG-A (AMBIGUO) y un "Joaquín" en SG-B
(FUERA_DE_SALA). Los demás niños/as del dataset quedan sin nombre (no se identifican por nombre en esta etapa).
Las notas de prueba están en `tests/fixtures/notas_prueba.json` (15 casos con resultado esperado).

## Contrato
Entrada (evento):
```json
{"texto":"Sofi y Pedro clasificaron hojas por tamaño. Hoy bajó la asistencia, mucha tos.",
 "id_educadora":"EDU-0001","sala_grupo":"SG-A","fecha":"2026-10-14"}
```
Salida:
```json
{"id_captura":"CAP-01J...","advertencias":[],
 "observaciones":[
  {"id_obs":"OBS-01JA…","tipo":"PARTICULAR","id_nino":"NINO-00123","texto_literal":"Sofi y Pedro clasificaron hojas por tamaño",
   "edad_meses":31,"evaluabilidad":"EVALUABLE",
   "nivel":9,"certeza":"alta","manifestaciones":[{"id_manifestacion":"MAN-L09-CO-02","nivel":9,"dominio":"cognitivo",
     "texto_observable":"Clasifica objetos por una característica visible…","certeza":"alta",
     "frase_evidencia":"clasificaron hojas por tamaño"}],
     "comentario":"Clasifica por una característica visible (tamaño) tras la actividad: nivel 9. Para su edad (31 meses) lo esperado es el nivel 9.",
     "niveles_esperados":[9],"comparacion_edad":"ACORDE",
   "estado":"SUGERIDO"},
  {"id_obs":"OBS-01JB…","tipo":"NO_IDENTIFICADO","texto_literal":"Sofi y Pedro clasificaron hojas por tamaño",
   "error_identificacion":"AMBIGUO",
   "candidatos":[{"id_nino":"NINO-00145","nombre":"Pedro A.","score":95},{"id_nino":"NINO-00160","nombre":"Pedro R.","score":95}]},
  {"id_obs":"OBS-01JC…","tipo":"GENERAL","texto_literal":"Hoy bajó la asistencia, mucha tos."}]}
```
Error de captura: `{"error":{"codigo":"SALA_DESCONOCIDA","mensaje":"..."}}`.

### Formato de las variables de los prompts (strings que arma `pipeline.py`)
- `{{nomina}}`: una línea por niño/a: `N1: Sofía M. — apodos: Sofi, la Sofi` (sin apodos: `N5: Pascal`). Las refs N1… son
  internas a la llamada; nunca se envía el `id_nino`.
- `{{niveles_descripcion}}`: una línea por nivel: `Nivel 8 — Combinación y participación: <descripcion>`. **Sin rangos de
  edad** (el LLM no debe tener pistas de edad).
- `{{candidatas}}`: una línea por código: `MAN-L08-LC-01 | lenguaje_comunicacion | <texto_observable>`, barajadas por corrida.
- `{{conductas_json}}`: la lista `conductas` devuelta por `extraer_conductas`, en JSON compacto.
- `{{ejemplos}}`: según `fewshot.json._formato`, separados por una línea en blanco.
- IDs: `CAP-<ulid>` y `OBS-<ulid>` (los del contrato son ilustrativos).

## Manejo de errores
| Situación | Comportamiento |
|---|---|
| Entrada inválida | error de captura, sin llamar al LLM |
| JSON inválido del LLM | 1 reintento con el error; luego `error_evaluacion = LLM_SALIDA_INVALIDA` en esa observación (el resto sigue) |
| Throttling Bedrock | backoff exponencial (máx. 4 intentos) |
| Fragmento no identificable | `NO_IDENTIFICADO` (no es falla del sistema) |
| Falla inesperada | log con `id_captura` y tipo de excepción (sin texto) y respuesta `{"error":{"codigo":"ERROR_INTERNO"}}` |

## Pruebas
- Unitarias: edad (tabla de referencia de `dominio.md` §1), nombres (apodos, tildes, "Naiara/Nayara", duplicados, fuera de sala),
  validaciones literales, consolidación de corridas (nivel, certeza, comentario), edad y comparación (tabla de `dominio.md` §1).
- LLM (`-m llm`): los 15 casos de `tests/fixtures/notas_prueba.json` con `tests/fixtures/nomina_demo.json`.
- `scripts/pipeline_local.py --texto "..." --educadora EDU-0001 --sala SG-A --fecha 2026-10-15` y `--casos tests/fixtures/notas_prueba.json` (corre todos e imprime tabla esperado vs obtenido).
- En AWS: `events/nota_ejemplo.json` + `sam remote invoke`.
