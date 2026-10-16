# Contratos congelados de Huellita en AWS

Fuente de verdad de los **8 carriles** que escriben este BFF, su plantilla, el frontend y
los scripts. Si el código y este archivo no calzan, manda este archivo. Nadie cambia una
firma, una ruta, un nombre de atributo ni un código de error sin cambiar primero este
documento. Está escrito para que un agente que **solo** lea este archivo escriba código que
encaje con el de los otros siete sin negociar.

Ya están terminados y **no se tocan**: `src/huellita_api/__init__.py`, `config.py`,
`modelos.py`, `datos/usuarias_demo.json`, `samconfig.toml`, `scripts/volcar_muestras.py`,
`tests/fixtures/*.json`, `.gitignore`, `pyproject.toml`, `CONTRATOS.md`.

Estilo obligatorio: docstrings y nombres en español, `from __future__ import annotations`,
tipos modernos (`str | None`), sin librerías fuera de `src/requirements.txt`
(fastapi, starlette, mangum, pydantic, boto3/botocore, tzdata; **no hay** paquete `ulid`).
Pruebas con `pytest` 9 (`requirements-dev.txt`) y `vitest` en el frontend.

## 0. Ajustes a la propuesta (lea esto primero)

- **Códigos de error en `snake_case` minúscula.** El spec exige `tope_diario` y
  `src/services/errores.ts` documenta `codigo` con ese ejemplo, igual que el transcriptor
  (`base64_invalido`, `audio_demasiado_grande`). Toda la tabla de §4 sigue esa forma.
- **`PUT /api/decisiones`** (no POST): lo dice la tarea 6 y es idempotente por definición.
- **`Evidencia.id == id_captura`**: las observaciones traen `id_captura`, así que
  `Sugerencia.evidenciaId` solo calza si la evidencia se llama igual. No hay dos ids.
- **Sin paquete `ulid`**: `ulid.nuevo_id_captura()` arma el ULID a mano (§6).
- **`foto` responde 422**, no 415: lo pide la tarea 5 ("foto u otro formato responde 422").
  El 415 queda reservado para el paso a través del transcriptor.
- **El BFF escribe `texto.json` también para audio** cuando el transcriptor termina
  (tarea 7: "La consulta además reintenta la entrega de texto.json"). El transcriptor
  escribe su propia copia; `texto_entregado` evita que el BFF la duplique.
- **`meta.json` lleva exactamente 3 claves** (§7). El script de referencia
  `integra-backend/scripts/subir_captura_prueba.py:57-62` agrega `"tipo"`, pero
  `integra-backend/src/core/modelos.py:222-233` lo declara `tipo: str | None = None` con
  `extra="ignore"`, así que omitirlo es seguro. Manda el spec.
- **Cabecera de usuaria `X-Usuaria-Id`**: el frontend no tiene cliente HTTP todavía, la
  define el BFF.
- **URL base `/api`, mismo origen**: `huellita-formato-mejorado/src/app/config.ts` dice que
  `VITE_DATOS=http` habla con el BFF en `/api`; CloudFront manda `/api/*` al BFF (§10).
- **CORS con `allow_origins=["*"]` y `allow_credentials=False`**: `config.py` está congelado
  y no tiene campo para el origen; la identificación demo va por cabecera, no por cookie.
- **Fuera de alcance del BFF**: `moverNino`, `darDeBaja`, `demoCapturas`, `reiniciarDemo`.
  Los resuelve el carril H en el cliente (§9).

## 1. Los 8 carriles

| Carril | Dueño exclusivo de | Depende de |
|---|---|---|
| A · Base pura | `src/huellita_api/errores.py`, `tiempo.py`, `mapeo.py`, `datos/__init__.py`, `datos/dynamo.py` | nada |
| B · Lectura | `src/huellita_api/datos/lectura.py`, `auth.py` | A |
| C · Capturas de texto | `src/huellita_api/ulid.py`, `s3.py`, `datos/capturas.py` | A |
| D · Decisiones | `src/huellita_api/datos/decisiones.py` | A |
| E · HTTP | `src/huellita_api/app.py`, `rutas/__init__.py`, `rutas/lectura.py`, `rutas/capturas.py`, `rutas/decisiones.py` | A, B, C, D, F |
| F · Audio | `src/huellita_api/transcriptor.py`, `datos/audio.py` | A, C |
| G · Infraestructura | `template.yaml`, `scripts/publicar_front.ps1` | — |
| H · Frontend y humo | `huellita-formato-mejorado/src/services/http.ts`, `…/src/services/captura.ts`, `…/src/app/servicios.tsx`, `…/src/pages/Revisar.tsx`, `huellita-web/scripts/smoke.py` | §4, §9 |

Las pruebas de cada carril viven en `tests/test_<carril>_*.py` (pytest) y junto al archivo
(`*.test.ts`) en el frontend. Nadie edita archivos de otro carril: si falta algo, se pide.

Quién importa a quién (no hay otras dependencias, y **no hay ciclos**):

```
app.py -> rutas/* -> (auth, datos/lectura, datos/capturas, datos/decisiones,
                      datos/audio, modelos, errores, config)
datos/lectura.py    -> (datos/dynamo, mapeo, tiempo, modelos, errores, config)
datos/capturas.py   -> (datos/dynamo, s3, ulid, tiempo, errores, config)
datos/decisiones.py -> (datos/dynamo, mapeo, tiempo, modelos, errores, config)
datos/audio.py      -> (datos/dynamo, datos/capturas, s3, transcriptor, tiempo, errores, config)
mapeo.py            -> (modelos, tiempo)        # puro: sin boto3, sin red, sin os.environ
transcriptor.py     -> (errores, config)        # urllib.request + boto3 apigateway
```

`cargar_config()` se llama **una sola vez** al importar `app.py`; el `Config` resultante se
pasa como primer argumento (`cfg`) a todo lo demás. Ningún módulo lee `os.environ` por su
cuenta. `cfg.sala_key("SG-A") == "JAR-0001#SG-A"`.

## 2. Firmas exactas

### `errores.py` (carril A)

```python
class ErrorApi(Exception):
    def __init__(self, codigo: str, mensaje: str) -> None: ...
    codigo: str
    mensaje: str

CODIGOS_HTTP: dict[str, int]   # la tabla completa de §4, codigo -> estado HTTP
MENSAJES: dict[str, str]       # codigo -> mensaje en las palabras de la tía
def error(codigo: str) -> ErrorApi: ...        # usa MENSAJES[codigo]
def estado_http(codigo: str) -> int: ...       # CODIGOS_HTTP.get(codigo, 500)
```

### `tiempo.py` (carril A)

```python
Reloj = Callable[[], datetime]                 # devuelve un datetime con huso

def ahora(cfg: Config) -> datetime: ...                      # datetime.now(ZoneInfo(cfg.zona_horaria))
def reloj_de(cfg: Config, reloj: Reloj | None) -> datetime: ...  # reloj() si viene, si no ahora(cfg)
def iso(momento: datetime) -> str: ...                       # "2026-10-15T14:05:57-03:00"
def dia(momento: datetime) -> str: ...                       # "2026-10-15"
def minutos_desde(creada_en: str, momento: datetime) -> float: ...
```

- `iso` usa `momento.isoformat(timespec="seconds")`.
- `minutos_desde` parsea con `datetime.fromisoformat`; si la marca no tiene huso se asume
  el de `momento`; si no se puede parsear devuelve `0.0` (no vence).
- `zoneinfo` necesita `tzdata`, que ya está en `src/requirements.txt`.

### `datos/dynamo.py` (carril A)

```python
def cliente() -> BaseClient: ...                      # boto3.client("dynamodb"), functools.cache
def consultar_todo(tabla: str, **parametros: object) -> list[dict]: ...
def obtener(tabla: str, clave: dict) -> dict | None: ...
def obtener_varios(tabla: str, claves: list[dict]) -> dict[str, dict]: ...
def poner(tabla: str, item: dict, condicion: str | None = None) -> bool: ...
def actualizar(
    tabla: str,
    clave: dict,
    expresion: str,
    valores: dict | None = None,
    condicion: str | None = None,
    nombres: dict[str, str] | None = None,
) -> dict | None: ...
def borrar(tabla: str, clave: dict) -> None: ...
```

- Todo entra y sale en formato AttributeValue (`{"S": "..."}`): este módulo no convierte nada.
- `consultar_todo` hace `query` paginado siguiendo `LastEvaluatedKey` y devuelve los ítems en
  el orden que entrega DynamoDB. Acepta `IndexName`, `KeyConditionExpression`, etc.
- `obtener_varios` hace `BatchGetItem` en lotes de 100 con reintento de `UnprocessedKeys`
  (hasta 3 vueltas) y devuelve `{valor_de_la_primera_clave: item}`.
- `poner` y `actualizar` devuelven `False` / `None` (no lanzan) cuando falla la condición
  (`ConditionalCheckFailedException`). `actualizar` usa `ReturnValues="ALL_NEW"`.
- Cualquier otro error de botocore se propaga; lo traduce `app.py` a `error_interno`.

### `mapeo.py` (carril A, funciones puras)

```python
def desanidar(valor: dict) -> object: ...
def a_jardin(item: dict) -> Jardin: ...
def a_salas(item_jardin: dict, cfg: Config) -> list[Sala]: ...
def a_nino(item: dict) -> Nino: ...
def a_evidencia_captura(item: dict, estado: EstadoEvidencia) -> Evidencia: ...
def a_evidencia_registro(item: dict, estado: EstadoEvidencia) -> Evidencia: ...
def a_sugerencia(item: dict) -> Sugerencia: ...
def estado_de_registro(estado: str | None) -> EstadoEvidencia: ...   # §8, tabla de traducción
def regla6(
    fila: dict,
    registro: dict | None,
    momento: datetime,
    minutos_max: int,
) -> EstadoEvidencia: ...
```

- `desanidar` resuelve `{"S"|"N"|"BOOL"|"L"|"M"|"NULL"}`; `{"N": "6"}` -> `int`, con punto -> `float`.
- `a_jardin` (tabla Jardines, `tests/fixtures/jardin.json`): `id = id_jardin`,
  `nombre = nombre_fantasia`, `comuna`, `region`.
- `a_salas`: el dataset solo trae `salas: ["SG-A", "SG-B"]`. Por cada sala que esté en
  `item_jardin["salas"]` **y** en `cfg.salas`, en el orden de `cfg.salas`:
  `id = "SG-A"`, `jardinId = id_jardin`, `nombre = f"Sala {id}"`,
  `nivelEducativo = "Sala Cuna Menor"`.
- `a_nino` (tabla Ninos): `id = id_nino`, `nombre`, `salaId = sala_grupo`,
  `fechaNacimiento = fecha_nacimiento`, `apellidoInicial = ""`, `activo = True`.
- `a_evidencia_captura` (tabla propia `Capturas`, §5): `id = id_captura`, `salaId = sala_id`,
  `autorId = autor_id`, `creadaEn = creada_en`, `formato`, `estado` (el argumento),
  `ninoIdSugerido = nino_id_sugerido`, `textoExtraido = texto_extraido`, `foto = None`.
- `a_evidencia_registro` (tabla Registros, `tests/fixtures/registros_sga.json`):
  `id = id_captura`, `salaId = sala_grupo`, `autorId = id_educadora`, `creadaEn = subido_en`,
  `formato`: `audio` si `tipo == "audio"`, `foto` si `tipo == "foto"`, `texto` en el resto
  (incluido `manual`); `estado` es el argumento; `textoExtraido = None`.
- `a_sugerencia` (tabla Observaciones, solo ítems con `origen == "app"`):

| Campo de `Sugerencia` | De dónde sale |
|---|---|
| `id` | `id_obs` |
| `evidenciaId` | `id_captura` |
| `salaId` | `sala_grupo` |
| `tipo` | `"nota_sala"` si `tipo == "GENERAL"`; `"evaluacion"` en el resto (`PARTICULAR`, `NO_IDENTIFICADO`) |
| `ninoId` | `id_nino` si está; si no, `None` |
| `nombreDetectado` | sin `id_nino`: `nombre` del candidato de mayor `score` en `candidatos` (`None` si la lista está vacía); con `id_nino`: `None` |
| `nucleo` | `dominio` de la manifestación elegida; `None` si no está en `modelos.NUCLEOS` |
| `nivel` | `nivel` del ítem si está entre 1 y 9; si no, el de la manifestación elegida; si no hay, `None` |
| `conducta` | `texto_observable` de la manifestación elegida |
| `cita` | `frase_evidencia` de la manifestación elegida; si falta, `texto_literal`; si falta, `""` |
| `certeza` | `certeza` del ítem; si no está: `"alta"` cuando `tipo == "GENERAL"`, `"baja"` en el resto |
| `estado` | `"pendiente"` (las decisiones las superpone `leer_registros`) |
| `validadaPor`, `validadaEn`, `original` | `None` |

Manifestación elegida: la primera de `manifestaciones` cuyo `nivel` sea igual al `nivel` del
ítem; si ninguna calza, la primera de la lista; si la lista está vacía, `nucleo`, `nivel` y
`conducta` quedan en `None` y la `cita` sale de `texto_literal`.

### `auth.py` (carril B)

```python
CABECERA_USUARIA = "X-Usuaria-Id"

def usuarias() -> list[Usuaria]: ...                      # datos/usuarias_demo.json, functools.cache
def usuaria_o_error(id_usuaria: str | None) -> Usuaria: ...
def exigir_sala(cfg: Config, usuaria: Usuaria, sala_id: str) -> None: ...
def existe(id_usuaria: str) -> bool: ...
```

- `usuarias()` lee la clave `"usuarias"` del JSON (ignora `_descripcion`): `EDU-0001` (Tía Ana,
  `SG-A`) y `EDU-0002` (Tía Rosa, `SG-B`).
- `usuaria_o_error(None)` o `""` -> `ErrorApi("sin_acceso", …)`; id desconocido ->
  `ErrorApi("autora_desconocida", …)`.
- `exigir_sala` -> `ErrorApi("sala_desconocida", …)` si `sala_id not in cfg.salas`, y
  `ErrorApi("sin_acceso", …)` si `sala_id not in usuaria.salaIds`. En ese orden.

### `datos/lectura.py` (carril B)

```python
def leer_contexto(cfg: Config) -> Contexto: ...
def leer_ninos(cfg: Config, sala_id: str) -> list[Nino]: ...
def leer_registros(cfg: Config, sala_id: str, reloj: Reloj | None = None) -> Registros: ...
```

- `leer_contexto`: `GetItem` en `cfg.tabla_jardines` con `{"id_jardin": {"S": cfg.jardin}}`;
  `jardin = a_jardin(item)`, `salas = a_salas(item, cfg)`, `usuarias = auth.usuarias()`.
  Si el jardín no existe -> `ErrorApi("no_encontrado", …)`.
- `leer_ninos`: `Query` a `cfg.tabla_ninos` con `KeyConditionExpression="id_jardin = :j"`,
  filtra en Python por `sala_grupo == sala_id`, mapea con `a_nino` y ordena por `nombre`.
- `leer_registros`, paso a paso:
  1. **Capturas propias**: `Query` al índice `porSala` de `cfg.tabla_capturas` por
     `sala_key = cfg.sala_key(sala_id)`. Se descartan los ítems de contador (§5).
  2. **Registros**: `BatchGetItem` (`dynamo.obtener_varios`) a `cfg.tabla_registros` **solo**
     con los `id_captura` de las filas **sin `estado_final`**. Las que ya lo tienen no
     consultan nada.
  3. **Estado de cada evidencia propia**: `mapeo.regla6(fila, registro, momento, cfg.minutos_max_procesando)`
     con `momento = tiempo.reloj_de(cfg, reloj)`. Ver §8.
  4. **Evidencias ajenas**: `Query` al índice `porSala` de `cfg.tabla_registros` por
     `sala_key`; se descartan los `id_captura` que ya vinieron del paso 1; el estado sale de
     `mapeo.estado_de_registro` más el vencimiento de la regla 6.
  5. **Sugerencias**: `Query` al índice `porSala` de `cfg.tabla_observaciones` por `sala_key`;
     se descartan los ítems con `origen != "app"`; se mapean con `a_sugerencia`.
  6. **Regla 5** (§8): a cada sugerencia con `ninoId is None` cuya captura propia tenga
     `nino_id_sugerido`, se le pone ese `ninoId`.
  7. `textoExtraido` vacío de una evidencia se rellena con el `texto_literal` de la primera
     observación de esa captura.
  8. **Decisiones** (regla 7, §8): `decisiones.leer_por_sala(cfg, cfg.sala_key(sala_id))` y
     `decisiones.aplicar(sugerencia, decision)` por cada sugerencia presente.
  9. `evidencias` ordenada por `creadaEn` **ascendente** (la última capturada al final, como
     espera `DataService.evidencias`) y `sugerencias` por `(evidenciaId, id)`.
- Cuando la regla 6 da un estado terminal **a partir de Registros**, `leer_registros` escribe
  `estado_final` en la fila (y `texto_extraido` si lo rellenó). Un `error` por vencimiento
  **no** se persiste: si el resultado llega tarde, todavía puede ganar.

### `ulid.py` (carril C)

```python
ALFABETO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"   # base32 de Crockford
RE_ID_CAPTURA: re.Pattern[str]                  # ^CAP-[0-9A-HJKMNP-TV-Z]{26}$

def nuevo_ulid(ms: int | None = None) -> str: ...
def nuevo_id_captura(ms: int | None = None) -> str: ...   # "CAP-01M503FN5942S3MNAFA14C07AQ"
def es_id_captura(valor: str) -> bool: ...
```

Ver §6 para el algoritmo exacto.

### `s3.py` (carril C)

```python
def cliente() -> BaseClient: ...                 # boto3.client("s3"), functools.cache
def clave_meta(id_captura: str) -> str: ...      # f"capturas/{id_captura}/meta.json"
def clave_texto(id_captura: str) -> str: ...     # f"capturas/{id_captura}/texto.json"
def cuerpo_meta(autor_id: str, sala_id: str, fecha: str) -> dict: ...
def cuerpo_texto(id_captura: str, texto: str, fuente: str = "manual") -> dict: ...
def subir_json(cfg: Config, clave: str, contenido: dict) -> None: ...
```

`subir_json` usa `Bucket=cfg.bucket_capturas`,
`Body=json.dumps(contenido, ensure_ascii=False).encode("utf-8")` y
`ContentType="application/json"`. Cualquier excepción se propaga tal cual: la traduce quien
llama a `ErrorApi("error_envio", …)`.

### `datos/capturas.py` (carril C)

```python
def reservar_cupo_del_dia(cfg: Config, sala_id: str, dia: str) -> int: ...
def contar_del_dia(cfg: Config, sala_id: str, dia: str) -> int: ...
def crear_fila(
    cfg: Config,
    *,
    id_captura: str,
    sala_id: str,
    autor_id: str,
    formato: str,
    creada_en: str,
    dia: str,
    nino_id_sugerido: str | None = None,
    mime_type: str | None = None,
) -> None: ...
def marcar_envio(
    cfg: Config,
    id_captura: str,
    estado_envio: str,
    *,
    id_trabajo: str | None = None,
    texto_entregado: bool | None = None,
) -> None: ...
def marcar_final(
    cfg: Config,
    id_captura: str,
    estado_final: str,
    *,
    texto_extraido: str | None = None,
) -> None: ...
def guardar_texto(cfg: Config, id_captura: str, texto: str) -> None: ...
def archivar(cfg: Config, id_captura: str, sala_id: str) -> bool: ...
def obtener(cfg: Config, id_captura: str) -> dict | None: ...
def leer_de_sala(cfg: Config, sala_id: str) -> list[dict]: ...
```

- `reservar_cupo_del_dia` es el **contador atómico** del tope diario: un solo `UpdateItem`
  sobre el ítem contador (§5) con
  `UpdateExpression="ADD n :uno"`,
  `ConditionExpression="attribute_not_exists(n) OR n < :tope"`,
  `:uno = 1`, `:tope = cfg.max_capturas_dia`, `ReturnValues="UPDATED_NEW"`.
  Devuelve el nuevo valor de `n`. Si la condición falla ->
  `ErrorApi("tope_diario", …)` (429). No hay lectura previa ni carrera posible.
- `contar_del_dia` lee el contador (`GetItem`) y devuelve `n` o `0`. Solo para pruebas y humo.
- `crear_fila` hace `PutItem` con `estado_envio = "enviando"`, sin `estado_final` y sin
  `archivada`. Devuelve `None`; la evidencia la arma quien llama.
- `marcar_envio` / `marcar_final` / `guardar_texto` hacen `UpdateItem` por `id_captura` y
  fijan `actualizado_en`. `marcar_final` acepta solo `"lista"` o `"error"`.
- `archivar` hace `UpdateItem` con `ConditionExpression="attribute_exists(id_captura) AND sala_key = :sk"`
  (`:sk = cfg.sala_key(sala_id)`) y `SET archivada = :si, estado_final = :lista`. Devuelve
  `False` si la condición falla (captura inexistente o de otra sala).
- `leer_de_sala` consulta el índice `porSala` y **filtra los ítems de contador** (los que no
  tienen `creada_en`).

### `datos/decisiones.py` (carril D)

```python
def guardar(
    cfg: Config,
    sala_key: str,
    id_sugerencia: str,
    *,
    estado: str,
    usuaria_id: str,
    validada_en: str,
    nino_id: str | None = None,
    nucleo: str | None = None,
    nivel: int | None = None,
    original: Original | None = None,
) -> None: ...
def borrar(cfg: Config, sala_key: str, id_sugerencia: str) -> None: ...
def leer_por_sala(cfg: Config, sala_key: str) -> dict[str, dict]: ...
def aplicar(sugerencia: Sugerencia, decision: dict) -> Sugerencia: ...
def decidir(sugerencia: Sugerencia, item: ItemDecision) -> tuple[str, Original | None]: ...
```

- `guardar` hace `PutItem` sin condición (pisa, por eso es idempotente). `estado` solo puede
  ser `"aceptada"`, `"cambiada"` o `"descartada"`; `"pendiente"` se guarda **borrando**.
- `leer_por_sala` hace `Query` por `sala_key` (es la clave de partición, §5) y devuelve
  `{id_sugerencia: item_desanidado}`.
- `decidir` es **pura** y es la regla 7 (§8): decide el estado final y el `original`.
- `aplicar` es **pura**: toma la sugerencia mapeada y la decisión guardada y devuelve la
  sugerencia con `estado`, `validadaPor`, `validadaEn`, `ninoId`, `nucleo`, `nivel` y
  `original` ya pisados. La reutiliza `datos/lectura.py`.

### `transcriptor.py` (carril F)

```python
class ErrorTranscriptor(Exception):
    def __init__(self, codigo: str, estado: int | None = None) -> None: ...
    codigo: str          # uno de los códigos de §4
    estado: int | None   # estado HTTP del transcriptor, si hubo respuesta

TIEMPO_POST = 10
TIEMPO_GET = 3

def valor_clave_api(cfg: Config) -> str: ...                              # functools.cache
def iniciar(cfg: Config, id_captura: str, audio_base64: str) -> str: ...  # -> "tr-<id_captura>"
def consultar(cfg: Config, id_trabajo: str) -> dict: ...                  # estado, texto_completo
```

- `valor_clave_api` llama **una sola vez** a
  `boto3.client("apigateway").get_api_key(apiKey=cfg.id_clave_transcriptor, includeValue=True)`
  y devuelve `respuesta["value"]`. La clave vive **solo en memoria**: no se escribe en logs,
  ni en respuestas, ni en archivos, ni se incluye en mensajes de excepción. Si falla ->
  `ErrorTranscriptor("transcriptor_caido")`.
- `iniciar`: `POST {cfg.url_transcriptor}/api/transcripciones/audio` con
  `x-api-key: valor_clave_api(cfg)`, `Content-Type: application/json` y cuerpo
  `{"id_captura": id_captura, "audio_base64": audio_base64}`. `urllib.request` con
  `timeout=TIEMPO_POST`. Acepta 200 y 202; devuelve `cuerpo["id_trabajo"]` y, si no viene,
  `f"tr-{id_captura}"`.
- `consultar`: `GET {cfg.url_transcriptor}/api/transcripciones/{id_trabajo}` con la misma
  cabecera y `timeout=TIEMPO_GET`. Devuelve el JSON parseado; quien llama lee solo
  `estado` (`transcribiendo` | `completado` | `fallido`) y `texto_completo`. Un 404 se
  devuelve como `{"estado": "fallido", "texto_completo": None}`.
- Traducción de errores del transcriptor (tarea 7):

| Transcriptor | `ErrorTranscriptor.codigo` | HTTP del BFF |
|---|---|---|
| 413 | `audio_demasiado_grande` | 413 |
| 415 | `formato_audio_no_soportado` | 415 |
| 429, 503 | `servicio_saturado` | 503 (mensaje con "intenta de nuevo") |
| 502, 504 | `transcriptor_caido` | 502 |
| otro 4xx/5xx, timeout, JSON ilegible, error de red | `transcriptor_caido` | 502 |

  Ninguna excepción cruda de `urllib`, `json` o `botocore` sale de este módulo.

### `datos/audio.py` (carril F)

```python
MAX_BYTES_AUDIO = 4194304
MAX_CONSULTAS_PARALELAS = 4

def decodificar(audio_base64: str) -> bytes: ...
def enviar(cfg: Config, id_captura: str, audio_base64: str) -> str: ...
def sincronizar(cfg: Config, sala_id: str, reloj: Reloj | None = None) -> None: ...
```

- `decodificar` usa `base64.b64decode(audio_base64, validate=True)`; si falla ->
  `ErrorApi("base64_invalido", …)` (422). Si `len(bytes) > MAX_BYTES_AUDIO` ->
  `ErrorApi("audio_demasiado_grande", …)` (413).
- `enviar` llama a `transcriptor.iniciar`, guarda el `id_trabajo` con
  `capturas.marcar_envio(cfg, id, "enviada", id_trabajo=…)` y lo devuelve. Un
  `ErrorTranscriptor` se vuelve `ErrorApi(e.codigo, …)` después de marcar la fila con
  `estado_envio = "error_envio"`.
- `sincronizar` recorre las filas de la sala con `formato == "audio"`, sin `estado_final` y
  con `id_trabajo`, y consulta `GET /api/transcripciones/tr-<id>` con un
  `ThreadPoolExecutor(max_workers=MAX_CONSULTAS_PARALELAS)`:
  - `fallido` -> `capturas.marcar_final(cfg, id, "error")`;
  - `completado` -> `capturas.guardar_texto(cfg, id, texto_completo)` y, si la fila no tiene
    `texto_entregado`, `s3.subir_json(cfg, s3.clave_texto(id), s3.cuerpo_texto(id, texto_completo, "audio"))`
    y `capturas.marcar_envio(cfg, id, "enviada", texto_entregado=True)` (**reintento de la
    entrega de `texto.json`**); el estado final lo pone Registros, no esta función;
  - `transcribiendo` -> no hace nada.
  Si una consulta o una escritura falla, se registra en el log y **la respuesta de
  `/registros` sigue igual**: `sincronizar` nunca lanza.

### `app.py` y `rutas/*` (carril E)

```python
app = FastAPI(title="Huellita BFF")
handler = Mangum(app, lifespan="off")
CFG = cargar_config()
```

- Los tres routers se incluyen con `prefix="/api"`.
- `CORSMiddleware` con `allow_origins=["*"]`, `allow_credentials=False`,
  `allow_methods=["GET", "POST", "PUT", "OPTIONS"]`,
  `allow_headers=["Content-Type", auth.CABECERA_USUARIA]`.
- Manejadores de excepción para `ErrorApi`, `RequestValidationError` (->
  `solicitud_invalida`), `StarletteHTTPException` (404/405 -> `no_encontrado`) y `Exception`
  (-> `error_interno`, 500). **Siempre** responden `RespuestaError`:
  `{"error": {"codigo": …, "mensaje": …}}`, con mensajes en las palabras de la tía: sin
  trazas, sin nombres de AWS, sin la clave del transcriptor.
- Las respuestas se serializan con `response_model_exclude_none=True`: los campos `None` no
  viajan y en TypeScript quedan `undefined`.
- Handler de Lambda: `huellita_api.app.handler`, `CodeUri: src/`.

## 3. Rutas HTTP

Base `/api`, mismo origen que el frontend. Todas las rutas salvo `/api/salud` y
`/api/contexto` exigen la cabecera `X-Usuaria-Id: EDU-0001`.

| Método y ruta | Entrada | Salida | Errores |
|---|---|---|---|
| `GET /api/salud` | — | `200 {"estado": "ok"}` | — |
| `GET /api/contexto` | — | `200 Contexto` | `no_encontrado` |
| `GET /api/salas/{salaId}/ninos` | cabecera | `200 list[Nino]` | `sin_acceso`, `sala_desconocida`, `autora_desconocida` |
| `GET /api/salas/{salaId}/registros` | cabecera | `200 Registros` | `sin_acceso`, `sala_desconocida`, `autora_desconocida` |
| `POST /api/capturas` | cabecera + `CapturaEntrada` | `201 CapturaCreada` | `solicitud_invalida`, `sin_acceso`, `autora_desconocida`, `sala_desconocida`, `formato_no_soportado`, `texto_invalido`, `base64_invalido`, `audio_demasiado_grande`, `formato_audio_no_soportado`, `tope_diario`, `error_envio`, `servicio_saturado`, `transcriptor_caido` |
| `POST /api/capturas/{idCaptura}/archivar` | cabecera + `{"salaId": "SG-A"}` | `200 {"evidencia": …}` | `sin_acceso`, `sala_desconocida`, `no_encontrado` |
| `PUT /api/decisiones` | cabecera + `DecisionesEntrada` | `200 SugerenciasActualizadas` | `solicitud_invalida`, `sin_acceso`, `autora_desconocida`, `sala_desconocida`, `sugerencia_desconocida`, `nino_de_otra_sala` |

Los modelos de entrada y salida son los de `modelos.py` (congelado, `extra="forbid"`,
campos en camelCase): `Contexto`, `Nino`, `Registros`, `CapturaEntrada`, `CapturaCreada`,
`DecisionesEntrada`, `SugerenciasActualizadas`, `RespuestaError`.

### `POST /api/capturas`, paso a paso (carril E)

1. `usuaria = auth.usuaria_o_error(cabecera)`; `auth.exigir_sala(cfg, usuaria, entrada.salaId)`.
2. `entrada.formato` tiene que ser `"texto"` o `"audio"`. Cualquier otro valor, **incluido
   `"foto"`** -> `formato_no_soportado` (**422**).
3. Validación del contenido:
   - `texto`: `entrada.texto` con `strip()` no vacío y de **1 a 5000** caracteres; si no ->
     `texto_invalido` (422).
   - `audio`: `entrada.audioBase64` presente; `audio.decodificar` valida base64
     (`base64_invalido`, 422) y tamaño (`audio_demasiado_grande`, 413).
4. `momento = tiempo.ahora(cfg)`; `dia = tiempo.dia(momento)` (fecha de Chile, `zoneinfo`).
   `capturas.reservar_cupo_del_dia(cfg, entrada.salaId, dia)` -> si no hay cupo,
   `tope_diario` (**429**).
5. `id_captura = ulid.nuevo_id_captura()`.
6. `capturas.crear_fila(...)` con `estado_envio = "enviando"` y `creada_en = tiempo.iso(momento)`.
7. `s3.subir_json(cfg, s3.clave_meta(id), s3.cuerpo_meta(entrada.autorId, entrada.salaId, dia))`.
   **Siempre primero.**
8. Según el formato:
   - `texto`: `s3.subir_json(cfg, s3.clave_texto(id), s3.cuerpo_texto(id, texto, "manual"))`.
   - `audio`: `audio.enviar(cfg, id, entrada.audioBase64)`, que guarda `id_trabajo = "tr-<id>"`.
9. `capturas.marcar_envio(cfg, id, "enviada")` y `201` con
   `{"evidencia": {..., "estado": "procesando"}}`.
10. Si **cualquier** escritura de los pasos 7 u 8 falla:
    `capturas.marcar_envio(cfg, id, "error_envio")` y `ErrorApi("error_envio", …)` (**502**).
    Para audio, los códigos del transcriptor manda la tabla de §2.

`entrada.autorId` tiene que ser igual a `usuaria.id`; si no -> `sin_acceso`.

### `GET /api/salas/{salaId}/registros` (carril E)

1. `auth.usuaria_o_error` + `auth.exigir_sala`.
2. `audio.sincronizar(cfg, sala_id)` (nunca lanza; ver §2).
3. `return lectura.leer_registros(cfg, sala_id)`.

Es la ruta que el frontend consulta cada 5 s mientras haya notas en `procesando`.

### `POST /api/capturas/{idCaptura}/archivar` (carril E)

`auth` + `exigir_sala(entrada.salaId)`; `capturas.archivar(cfg, idCaptura, salaId)`;
si devuelve `False` -> `no_encontrado` (404). Si no, responde la evidencia ya en `lista`.

### `PUT /api/decisiones` (carril E, regla 7)

1. `auth.usuaria_o_error` + `auth.exigir_sala(cfg, usuaria, entrada.salaId)`;
   `entrada.usuariaId` tiene que ser igual a `usuaria.id`, si no -> `sin_acceso`.
2. Lee las sugerencias de la sala (`lectura.leer_registros(cfg, entrada.salaId).sugerencias`)
   y las indexa por `id`.
3. Por cada `ItemDecision`, en orden:
   - si el `idSugerencia` no está en ese índice -> `sugerencia_desconocida` (422). Esto cubre
     los `id_obs` del dataset (`origen == "dataset"`, `id_captura == "DATASET"`), que nunca
     son sugerencias de la app;
   - si trae `cambios` y `cambios.ninoId` no es un niño/a de `entrada.salaId` ->
     `nino_de_otra_sala` (422). El núcleo y el nivel ya los valida pydantic (`NucleoId`,
     `Nivel` 1..9), así que un dominio inválido o un nivel 10 dan `solicitud_invalida` (422).
4. `estado, original = decisiones.decidir(sugerencia, item)`:
   - `item.estado == "pendiente"` -> `decisiones.borrar(...)`;
   - en el resto -> `decisiones.guardar(...)` con `usuaria_id = entrada.usuariaId` y
     `validada_en = tiempo.iso(tiempo.ahora(cfg))`.
5. Responde `SugerenciasActualizadas` con **todas** las sugerencias de la sala ya actualizadas
   (se vuelve a aplicar `decisiones.aplicar` sobre las leídas en el paso 2; no hace falta otra
   lectura completa).

Nada se escribe si alguna validación falla: se valida **la solicitud completa antes** de
escribir. Repetir la misma llamada da el mismo resultado (mismos cuerpos, mismo HTTP) salvo
`validadaEn`, que es la marca de la última llamada.

## 4. Códigos de error estables

Nombre estable en `errores.CODIGOS_HTTP`. El cuerpo es siempre
`{"error": {"codigo": …, "mensaje": …}}`.

| `codigo` | HTTP | Cuándo |
|---|---|---|
| `sin_acceso` | 403 | falta `X-Usuaria-Id`, la sala no es de la usuaria, o `autorId`/`usuariaId` no calza con la cabecera |
| `autora_desconocida` | 404 | el id de la cabecera no está en `usuarias_demo.json` |
| `sala_desconocida` | 404 | `salaId` fuera de `SALAS_DEMO` |
| `no_encontrado` | 404 | jardín, captura o ruta inexistente |
| `solicitud_invalida` | 422 | el cuerpo no valida (pydantic): campo extra, núcleo inválido, nivel 10, lista vacía o de más de 50 ítems |
| `formato_no_soportado` | 422 | `formato` distinto de `texto` o `audio` (incluye `foto`) |
| `texto_invalido` | 422 | `texto` vacío tras `strip()` o de más de 5000 caracteres |
| `base64_invalido` | 422 | `audioBase64` que no decodifica |
| `sugerencia_desconocida` | 422 | `idSugerencia` que no es sugerencia `origen=app` de esa sala (incluye ids del dataset) |
| `nino_de_otra_sala` | 422 | `cambios.ninoId` no pertenece a `salaId` |
| `audio_demasiado_grande` | 413 | audio decodificado sobre 4194304 bytes, o 413 del transcriptor |
| `formato_audio_no_soportado` | 415 | 415 del transcriptor |
| `tope_diario` | 429 | la sala llegó a `MAX_CAPTURAS_DIA` capturas hoy |
| `servicio_saturado` | 503 | 429 o 503 del transcriptor; el mensaje incluye "intenta de nuevo" |
| `error_envio` | 502 | falló una escritura en S3 |
| `transcriptor_caido` | 502 | 502, 504, timeout o error de red del transcriptor |
| `error_interno` | 500 | cualquier otra excepción |

## 5. Tablas propias del BFF

Las crea `template.yaml` (carril G) con `BillingMode: PAY_PER_REQUEST`. Los nombres reales
llegan por entorno (`TABLA_CAPTURAS`, `TABLA_DECISIONES`): nunca se escriben en el código.

### `TablaCapturas`

| | Clave | Tipo |
|---|---|---|
| Partición | `id_captura` | `S` — `"CAP-01M503FN5942S3MNAFA14C07AQ"`, igual al `id_captura` de Registros y al `Evidencia.id` |

Índice `porSala` (GSI, `ProjectionType: ALL`): partición `sala_key` (`S`), orden `creada_en`
(`S`). Es **disperso**: los ítems de contador no llevan `sala_key`, así que no aparecen.

Atributos de una fila de captura:

| Atributo | Tipo | Qué guarda |
|---|---|---|
| `sala_key` | `S` | `"JAR-0001#SG-A"` (`cfg.sala_key`) |
| `creada_en` | `S` | ISO-8601 con huso: `"2026-10-15T14:05:57-03:00"` |
| `sala_id` | `S` | `"SG-A"` |
| `autor_id` | `S` | `"EDU-0001"` |
| `dia` | `S` | `"2026-10-15"`, fecha de Chile (`cfg.zona_horaria`) |
| `formato` | `S` | `"texto"` \| `"audio"` |
| `estado_envio` | `S` | `"enviando"` \| `"enviada"` \| `"error_envio"` |
| `estado_final` | `S` | opcional: `"lista"` \| `"error"`. Mientras no exista, hay que mirar Registros |
| `archivada` | `BOOL` | opcional: `true` cuando la tía archivó la nota |
| `nino_id_sugerido` | `S` | opcional: el niño/a desde cuya ficha se capturó (regla 5) |
| `texto_extraido` | `S` | opcional: texto escrito por la tía o transcrito |
| `id_trabajo` | `S` | opcional, solo audio: `"tr-<id_captura>"` |
| `texto_entregado` | `BOOL` | opcional, solo audio: `texto.json` ya escrito por el BFF |
| `mime_type` | `S` | opcional, solo audio: lo que mandó el navegador |
| `actualizado_en` | `S` | ISO con huso de la última escritura |

Ítem **contador atómico** del tope diario, en la misma tabla:

| Atributo | Tipo | Valor |
|---|---|---|
| `id_captura` | `S` | `"CONTADOR#JAR-0001#SG-A#2026-10-15"` = `f"CONTADOR#{cfg.sala_key(sala_id)}#{dia}"` |
| `n` | `N` | capturas aceptadas hoy en esa sala |

No lleva `sala_key` ni `creada_en`, así que queda fuera del índice `porSala`. Se incrementa
con un único `UpdateItem` condicional (§2, `reservar_cupo_del_dia`): esa es la única forma
legítima de contar el tope.

### `TablaDecisiones`

| | Clave | Tipo |
|---|---|---|
| Partición | `sala_key` | `S` — `"JAR-0001#SG-A"` |
| Orden | `id_sugerencia` | `S` — el `id_obs` de Observaciones |

Queda **consultable por `sala_key`** con un `Query` directo, sin índices. Atributos:

| Atributo | Tipo | Qué guarda |
|---|---|---|
| `estado` | `S` | `"aceptada"` \| `"cambiada"` \| `"descartada"` (nunca `"pendiente"`: eso se borra) |
| `usuaria_id` | `S` | `"EDU-0001"` |
| `validada_en` | `S` | ISO con huso |
| `nino_id` | `S` | opcional: valor final tras la corrección |
| `nucleo` | `S` | opcional: valor final |
| `nivel` | `N` | opcional: valor final, 1..9 |
| `orig_nino_id` | `S` | opcional: lo que propuso la IA (solo si `estado == "cambiada"`) |
| `orig_nucleo` | `S` | opcional: idem |
| `orig_nivel` | `N` | opcional: idem |

### Tablas ajenas (solo lectura, las crea `integra-backend/template.yaml`)

| Tabla | Clave | Acceso del BFF |
|---|---|---|
| Jardines | `id_jardin` | `GetItem` |
| Ninos | `id_jardin` + `id_nino` | `Query` por `id_jardin` |
| Registros | `id_captura`; GSI `porSala` (`sala_key` + `subido_en`) | `Query` en `porSala`, `BatchGetItem` por `id_captura` |
| Observaciones | `id_captura` + `id_obs`; GSI `porSala` (`sala_key` + `orden`) | `Query` en `porSala` |
| Educadoras | `id_educadora` | no se usa: las tías salen de `usuarias_demo.json` |

Confirmado en `integra-backend/template.yaml:91-150`.

## 6. Formato del `id_captura`

`CAP-<ULID>`, lo exige `ProcesarNota`
(`integra-backend/src/core/capturas.py:21` usa el mismo patrón).

- Alfabeto: base32 de Crockford, `"0123456789ABCDEFGHJKMNPQRSTVWXYZ"` (sin `I`, `L`, `O`, `U`).
- 128 bits: **48 bits de tiempo en milisegundos** (`time.time_ns() // 1_000_000`) en la parte
  alta, y **80 bits aleatorios** de `secrets.token_bytes(10)` en la parte baja:

  ```python
  valor = (ms & ((1 << 48) - 1)) << 80 | int.from_bytes(secrets.token_bytes(10), "big")
  ```

- Se escriben 26 caracteres, del más significativo al menos significativo, 5 bits cada uno
  (`26 * 5 = 130` bits: el primer carácter solo lleva 2 bits útiles, por eso nunca pasa de `7`).
- Regex obligatorio: `^CAP-[0-9A-HJKMNP-TV-Z]{26}$` (`ulid.RE_ID_CAPTURA`).
- Ejemplo real de la cuenta del hackathon: `CAP-01M503FN5942S3MNAFA14C07AQ`.

## 7. Claves y cuerpos en S3

Bucket `cfg.bucket_capturas` (`integra-capturas-277702547089`), prefijo fijo:

```
capturas/{id_captura}/meta.json          lo escribe el BFF, SIEMPRE primero
capturas/{id_captura}/texto.json         lo escribe el BFF (texto, y audio al completarse)
capturas/{id_captura}/original/audio.*   lo copia el transcriptor; el BFF no lo toca
```

`meta.json`, **exactamente** estas tres claves, en este orden:

```json
{"id_educadora": "EDU-0001", "sala_grupo": "SG-A", "fecha_observacion": "2026-10-15"}
```

- `id_educadora` = `entrada.autorId`; `sala_grupo` = `entrada.salaId`;
  `fecha_observacion` = fecha de **Chile** (`cfg.zona_horaria`, `zoneinfo`), `AAAA-MM-DD`.
- UTF-8 (`ensure_ascii=False` + `.encode("utf-8")`) y `ContentType="application/json"`.

`texto.json`, **exactamente** estas tres claves:

```json
{"id_captura": "CAP-…", "fuente": "manual", "partes": [{"texto": "Nayara apiló cinco cubos y dijo torre"}]}
```

- `fuente` es `"manual"` para el formato texto y `"audio"` cuando lo escribe el reintento de
  entrega del audio.
- **`meta.json` se escribe antes que `texto.json`.** Si llega al revés, `ProcesarNota` marca
  la captura en `ERROR` (`servicio_transcripcion/README.md`, sección "Entrega a ProcesarNota").
- El BFF nunca borra ni lee objetos de este bucket: solo `PutObject`.

## 8. Las reglas 5, 6 y 7

### Regla 5 · `nino_id_sugerido` a las `NO_IDENTIFICADO`

Cuando la tía captura desde la ficha de un niño/a, la fila de `Capturas` guarda
`nino_id_sugerido`. Al leer los registros, cada `Sugerencia` con `ninoId is None` (viene de una
observación `tipo == "NO_IDENTIFICADO"`, o `PARTICULAR` sin resolver) cuya `evidenciaId`
corresponda a una captura propia con `nino_id_sugerido` recibe `ninoId = nino_id_sugerido`.
`nombreDetectado`, `certeza`, `nucleo` y `nivel` no se tocan. Si la sugerencia ya tiene
`ninoId`, no se cambia nunca.

### Regla 6 · Estado de la evidencia

`mapeo.estado_de_registro(estado_registro)` traduce el estado de la tabla `Registros` de
integra-procesador a `EstadoEvidencia` (`modelos.py`):

| `Registros.estado` | `Evidencia.estado` |
|---|---|
| `RECIBIDO` | `procesando` |
| `PROCESANDO` | `procesando` |
| `PROCESADO` | `lista` |
| `SIN_TEXTO` | `error` |
| `ERROR` | `error` |
| sin fila todavía, o valor desconocido | `procesando` |

`SIN_TEXTO` va a `error` porque para la tía significa "no pudimos leerla", y Revisar le ofrece
"Escribirla" o "Descartar", que es el camino de `error`.

`mapeo.regla6(fila, registro, momento, minutos_max)` decide el estado de una captura propia,
en este orden:

1. `fila.archivada is True` -> `"lista"`.
2. `fila.estado_final` presente -> ese valor.
3. `fila.estado_envio == "error_envio"` -> `"error"`.
4. `fila.estado_envio == "enviando"` -> `"procesando"`, y sigue al paso 6.
5. (`estado_envio == "enviada"`) -> `estado_de_registro(registro.estado if registro else None)`.
6. Vencimiento: si el resultado es `"procesando"` y
   `tiempo.minutos_desde(fila.creada_en, momento) > minutos_max` -> `"error"`.
   `minutos_max` es `cfg.minutos_max_procesando` (20 en el despliegue).

`leer_registros` persiste `estado_final` solo cuando el estado terminal viene del paso 5; el
`error` por vencimiento no se guarda.

### Regla 7 · Semántica de `PUT /api/decisiones`

`decisiones.decidir(sugerencia, item)` es pura y tiene **cinco transiciones**. `item.estado`
solo puede valer `aceptada`, `descartada` o `pendiente` (`modelos.ItemDecision`, congelado);
`cambiada` lo decide el servidor.

| # | Entrada | Estado guardado | `original` | Qué se escribe |
|---|---|---|---|---|
| 1 | `aceptada` sin `cambios` | `aceptada` | `None` | `guardar` con los valores de la sugerencia |
| 2 | `aceptada` con `cambios` que **difieren** de la sugerencia | `cambiada` | `{ninoId, nucleo, nivel}` **previos** (los de la IA) | `guardar` con los valores nuevos |
| 3 | `aceptada` con `cambios` **iguales** a los de la IA | `aceptada` | `None` | `guardar` con los mismos valores |
| 4 | `descartada` | `descartada` | `None` | `guardar` |
| 5 | `pendiente` | — | — | `borrar` (la sugerencia vuelve a `pendiente`) |

En las transiciones 1 a 4: `validadaPor = entrada.usuariaId` y
`validadaEn = tiempo.iso(tiempo.ahora(cfg))`. En la 5 los dos quedan en `None`. Es la misma
regla que `DataServiceLocal.validar` en el frontend
(`huellita-formato-mejorado/src/services/datos.ts`), así que local y AWS se ven igual.

La comparación de la transición 2 es campo a campo contra la sugerencia **leída de
Observaciones** (no contra lo que mande el cliente): se comparan `ninoId`, `nucleo` y `nivel`.

Idempotencia: `guardar` es un `PutItem` sin condición y `borrar` un `DeleteItem`, así que
repetir la llamada deja la misma fila y responde lo mismo (salvo `validadaEn`).

## 9. Frontend (carril H)

`CONFIG.datos === 'http'` (de `VITE_DATOS=http`) elige el servicio de AWS. `src/app/config.ts`,
`src/lib/tipos.ts`, `src/services/datos.ts` (la interfaz `DataService`), `src/services/ia.ts` y
`src/services/errores.ts` ya existen y **no cambian de forma**.

### `src/services/http.ts` (nuevo)

```ts
export const BASE = '/api';
export const CABECERA_USUARIA = 'X-Usuaria-Id';
export const INTERVALO_SONDEO_MS = 5000;
export const CLAVE_SESION = 'huellita:aws:v1';

export function aBase64(bytes: Uint8Array): string;
export async function blobABase64(blob: Blob): Promise<string>;
export class DataServiceHttp implements DataService {
  readonly procesaEnServidor = true;
  readonly admiteFoto = false;
}
export const servicioHttp: DataService;
```

- `aBase64` recorre el `Uint8Array` en **bloques de `0x8000`** y los pasa por
  `String.fromCharCode(...bloque)`, concatena y aplica `btoa` una sola vez al final.
  `blobABase64` hace `new Uint8Array(await blob.arrayBuffer())` y llama a `aBase64`.
- Toda respuesta con error se convierte en
  `new ErrorParaTia(cuerpo.error.mensaje, cuerpo.error.codigo, respuesta.status)`
  (`src/services/errores.ts`). Si el cuerpo no es el JSON esperado, el mensaje es
  "No pudimos guardar esto. Intenta de nuevo." y el `codigo` queda `undefined`.
- Cada llamada manda `CABECERA_USUARIA` con la usuaria elegida.

Comportamiento de cada método de `DataService`:

| Método | Qué hace la versión HTTP |
|---|---|
| `hoy()` | `CONFIG.fechaHoy` si está; si no, la fecha de hoy en `America/Santiago` (`Intl.DateTimeFormat('en-CA', { timeZone })`) |
| `sesion`, `usuarias`, `jardin`, `salas`, `salasDelJardin`, `salaActual` | de `GET /api/contexto`, cacheado en memoria |
| `usuariaElegida`, `cambiarUsuaria`, `cambiarSala` | `localStorage[CLAVE_SESION]` con `{ usuariaId, salaId, elegida }`; no hay llamada al servidor |
| `ninos(salaId)` | `GET /api/salas/{salaId}/ninos` |
| `nino(id)` | del caché de la sala actual; si no está, busca en las salas visibles |
| `evidencias(filtro)`, `sugerencias(filtro)` | del último `GET /api/salas/{salaId}/registros`, filtrado en el cliente igual que `DataServiceLocal` |
| `demoCapturas()` | `[]` |
| `guardarEvidencia(e, archivo?)` | `POST /api/capturas` (ver abajo) |
| `marcarEvidencia(id, estado, …)` | solo si `estado === 'lista'` **y** la evidencia está en `error`: `POST /api/capturas/{id}/archivar`. En cualquier otro caso **no hace nada**: los estados de proceso los define el servidor |
| `guardarSugerencias(previas)` | un solo `PUT /api/decisiones` con un ítem por sugerencia (ver abajo) |
| `validar(id, cambios?)` | `PUT /api/decisiones` con **un** ítem `{ idSugerencia: id, estado: 'aceptada', cambios? }` |
| `descartar(id)` | `PUT /api/decisiones` con **un** ítem `{ idSugerencia: id, estado: 'descartada' }` |
| `moverNino`, `darDeBaja` | lanzan `new ErrorParaTia('Esto todavía no se puede hacer desde aquí.', 'no_disponible')` |
| `suscribir(cb)` | registra `cb` y sondea `GET /api/salas/{salaId}/registros` (ver abajo) |
| `reiniciarDemo()` | borra `localStorage[CLAVE_SESION]` y el caché; no llama al servidor |

- `guardarEvidencia` arma `CapturaEntrada`: `salaId`, `autorId` (la usuaria de la sesión),
  `formato`, y
  - texto: `texto` con el texto tal cual (ya recortado por la pantalla);
  - audio: `audioBase64 = await blobABase64(archivo)` y `mimeType = archivo.type`.
  Devuelve `respuesta.evidencia`, que ya viene en `procesando`.
- `guardarSugerencias(previas)` manda **una sola** llamada con un ítem por sugerencia, con
  este mapeo: `aceptada` -> `{estado: 'aceptada'}`; `cambiada` -> `{estado: 'aceptada',
  cambios: {ninoId, nucleo, nivel}}` con los valores **actuales** de la sugerencia;
  `descartada` -> `{estado: 'descartada'}`; `pendiente` -> `{estado: 'pendiente'}` (borra la
  decisión). Es lo que usa Deshacer.
- **Actualización optimista**: `validar`, `descartar` y `guardarSugerencias` pisan el caché
  local y avisan a los suscriptores **antes** de la llamada; si la llamada falla, se restaura
  el caché anterior, se avisa de nuevo y se propaga el `ErrorParaTia`.
- `suscribir` mantiene un `setInterval` de `INTERVALO_SONDEO_MS` que solo existe **mientras
  el último `Registros` tenga al menos una evidencia en `procesando`**; cuando no queda
  ninguna, el intervalo se limpia. Vuelve a arrancar cuando una captura nueva entra en
  `procesando`. La baja que devuelve `suscribir` quita el `cb` y, si era el último, el
  intervalo.

### `src/services/captura.ts`

`capturar(formato, archivo?, texto?, ninoId?, servicios?)` mantiene su firma y su
`ResultadoCaptura`. El único cambio: si `datos.procesaEnServidor === true`, después de
`datos.guardarEvidencia(...)` **no** se llama a `ia.procesar`, ni a `datos.guardarSugerencias`,
ni a `datos.marcarEvidencia`; `procesada` se resuelve con `[]`. El servidor procesa y el
sondeo de `suscribir` trae las sugerencias.

### `src/app/servicios.tsx`

`PREDETERMINADOS.datos` pasa a ser
`CONFIG.datos === 'http' ? servicioHttp : servicioDatos`. Nada más cambia: las pantallas
siguen usando `useServicios()`.

### `src/pages/Revisar.tsx`

No cambia su lógica. "Confirmar los de confianza alta" sigue llamando a `datos.validar` una
vez por sugerencia (N llamadas de un ítem cada una); Deshacer sigue llamando a
`datos.guardarSugerencias(previas)` (una sola llamada); la nota en `error` sigue llamando a
`datos.marcarEvidencia(id, 'lista')`, que ahora archiva en el servidor.

## 10. Infraestructura (carril G)

`huellita-web/template.yaml` es nuevo. **Los parámetros tienen que calzar exactamente con
`samconfig.toml`** (congelado): `TablaJardines`, `TablaEducadoras`, `TablaNinos`,
`TablaRegistros`, `TablaObservaciones`, `BucketCapturas`, `UrlTranscriptor`,
`IdClaveTranscriptor`, `JardinDemo`, `SalasDemo`, `MaxCapturasDia`, `MinutosMaxProcesando`.
Cualquier parámetro adicional necesita `Default`. `ZONA_HORARIA` se fija a
`America/Santiago` directo en el entorno de la función, sin parámetro.

Nombres de recursos congelados (los citan los otros carriles y los scripts):

| Recurso | Tipo | Notas |
|---|---|---|
| `TablaCapturas` | `AWS::DynamoDB::Table` | §5, GSI `porSala` |
| `TablaDecisiones` | `AWS::DynamoDB::Table` | §5, sin GSI |
| `ApiHttp` | `AWS::Serverless::HttpApi` | explícita, para poder declarar `RouteSettings` |
| `FuncionBff` | `AWS::Serverless::Function` | `CodeUri: src/`, `Handler: huellita_api.app.handler`, python3.13 |
| `BucketWeb` | `AWS::S3::Bucket` | privado, `PublicAccessBlockConfiguration` en `true`, AES256 |
| `PoliticaBucketWeb` | `AWS::S3::BucketPolicy` | solo `s3:GetObject` para `cloudfront.amazonaws.com` con `AWS:SourceArn` de `Distribucion` |
| `OacWeb` | `AWS::CloudFront::OriginAccessControl` | `OriginAccessControlOriginType: s3`, `SigningBehavior: always`, `SigningProtocol: sigv4` |
| `FuncionSpa` | `AWS::CloudFront::Function` | reescribe a `/index.html` las rutas sin extensión |
| `Distribucion` | `AWS::CloudFront::Distribution` | dos orígenes: `BucketWeb` (con OAC) y el dominio de `ApiHttp` |

- `FuncionBff` lleva en el entorno: `TABLA_JARDINES`, `TABLA_EDUCADORAS`, `TABLA_NINOS`,
  `TABLA_REGISTROS`, `TABLA_OBSERVACIONES`, `TABLA_CAPTURAS`, `TABLA_DECISIONES`,
  `BUCKET_CAPTURAS`, `URL_TRANSCRIPTOR`, `ID_CLAVE_TRANSCRIPTOR`, `JARDIN_DEMO`,
  `SALAS_DEMO`, `MAX_CAPTURAS_DIA`, `MINUTOS_MAX_PROCESANDO`, `ZONA_HORARIA`
  (los mismos nombres que lee `config.py`, congelado).
- Eventos de `FuncionBff`: `Catchall` (`Path: /{proxy+}`, `Method: ANY`) y `Capturas`
  (`Path: /api/capturas`, `Method: POST`), las dos con `ApiId: !Ref ApiHttp`.
- `ApiHttp.RouteSettings`: `"POST /api/capturas"` con `ThrottlingRateLimit: 5` y
  `ThrottlingBurstLimit: 10`.
- Permisos de `FuncionBff`, **nada más que esto**:
  - `dynamodb:GetItem`, `dynamodb:Query`, `dynamodb:BatchGetItem` sobre Jardines,
    Educadoras, Ninos, Registros, Observaciones y sus `index/*`;
  - `dynamodb:GetItem`, `Query`, `PutItem`, `UpdateItem`, `DeleteItem`, `BatchGetItem` sobre
    `TablaCapturas`, `TablaDecisiones` y sus `index/*` (`DynamoDBCrudPolicy` sobre Capturas y
    sobre Decisiones);
  - `s3:PutObject` **acotado** a `arn:aws:s3:::${BucketCapturas}/capturas/*`;
  - `apigateway:GET` **acotado** a
    `!Sub "arn:aws:apigateway:${AWS::Region}::/apikeys/${IdClaveTranscriptor}"`.
- `Distribucion`:
  - comportamiento por defecto -> origen `BucketWeb` con `OacWeb`, solo `GET`/`HEAD`,
    `ViewerProtocolPolicy: redirect-to-https`, política de caché administrada `CachingOptimized`,
    y `FunctionAssociations` con `FuncionSpa` en `viewer-request`;
  - comportamiento `/api/*` -> origen `ApiHttp`, **todos** los métodos, política de caché
    administrada `CachingDisabled`, política de origen que reenvía todas las cabeceras
    **menos `Host`** y todos los `query strings` (`AllViewerExceptHostHeader`);
  - **sin `CustomErrorResponses`**: aplican a toda la distribución y convertirían los 404 y
    403 de la API en `index.html`.
- `FuncionSpa` (CloudFront Functions, JS runtime 2.0): si `request.uri` no tiene punto en el
  último segmento, lo cambia a `/index.html`. Nada más.
- Outputs obligatorios: `UrlApp` (`https://` + `Distribucion.DomainName`), `BucketWeb`
  (`!Ref BucketWeb`), `IdDistribucion` (`!Ref Distribucion`), más `UrlApi`
  (`ApiHttp` endpoint), `TablaCapturasNombre` y `TablaDecisionesNombre`.

### `huellita-web/scripts/publicar_front.ps1`

PowerShell, sin parámetros obligatorios. Pasos, en este orden:

1. Lee los outputs del stack `huellita-web` con
   `aws cloudformation describe-stacks --profile hackaton --region us-east-1`:
   `UrlApp`, `BucketWeb`, `IdDistribucion`.
2. En `huellita-formato-mejorado/`: `npm ci`, luego `npm run build` con
   `$env:VITE_DATOS="http"`.
3. Sube en **dos pasadas** con `aws s3 sync dist s3://<BucketWeb> --delete`:
   - primera: solo `assets/*`, con `--cache-control "public,max-age=31536000,immutable"`;
   - segunda: todo lo demás (incluidos `index.html`, `sw.js`, `registerSW.js` y
     `manifest.webmanifest`), con `--cache-control "no-cache"`, para que la PWA se actualice.
4. `aws cloudfront create-invalidation --distribution-id <IdDistribucion> --paths "/*"`.
5. Imprime `UrlApp`.

Separador de comandos `;` (nunca `&&`) y variables `$env:NOMBRE`: es PowerShell en Windows.

Plan B si la cuenta no permite crear CloudFront: la Lambda del BFF sirve también el build
desde el mismo dominio de la API (monta los archivos estáticos y deja `/api/*` como está),
y hay que **avisarlo** en el reporte.

### `huellita-web/scripts/smoke.py`

Solo biblioteca estándar, al estilo de `servicio_transcripcion/scripts/probar_audio.py`.
Recibe la URL base como primer argumento (`python scripts/smoke.py https://d123.cloudfront.net`).
Pasos: `GET /api/salud`; `GET /api/contexto`; `GET /api/salas/SG-A/ninos`;
`POST /api/capturas` con formato texto y un nombre conocido de `SG-A`; espera a que la
evidencia quede `lista` sondeando `GET /api/salas/SG-A/registros` cada 5 s con un máximo de
**5 minutos**; `PUT /api/decisiones` confirmando una de sus sugerencias; vuelve a leer y
comprueba que quedó `aceptada`. Cabecera `X-Usuaria-Id: EDU-0001` en todo. Sale con 0 si todo
pasó y con 1 describiendo el primer paso que falló.

## 11. Confirmado contra lo real (solo lectura)

| Qué | Dónde se confirmó | Resultado |
|---|---|---|
| Claves e índices de Registros y Observaciones | `integra-backend/template.yaml:91-150` | `Registros`: PK `id_captura`, GSI `porSala` (`sala_key` + `subido_en`). `Observaciones`: PK `id_captura` + SK `id_obs`, GSI `porSala` (`sala_key` + `orden`) |
| Bucket de capturas con nombre fijo | `integra-backend/template.yaml:159-172` | `integra-capturas-${AWS::AccountId}`, privado y cifrado |
| Disparo de `ProcesarNota` | `integra-backend/template.yaml:196-224` | notificaciones S3 por sufijo `meta.json` y `texto.json` bajo `capturas/` |
| Cuerpos de `meta.json` y `texto.json` | `integra-backend/scripts/subir_captura_prueba.py:57-68` | iguales a §7, **salvo** que el script agrega `"tipo"` |
| `"tipo"` es opcional | `integra-backend/src/core/modelos.py:222-233` | `Meta` tiene `tipo: str \| None = None` y `extra="ignore"`: omitirlo es seguro |
| `fuente` y `partes` de `texto.json` | `integra-backend/src/core/modelos.py:236-260` | `TextoCaptura.fuente` opcional, `Parte.texto` obligatorio |
| Estados de Registros | `integra-backend/src/handler.py:5-8` | `RECIBIDO`, `PROCESANDO`, `PROCESADO`, `SIN_TEXTO`, `ERROR` |
| Formato del `id_captura` | `integra-backend/src/core/capturas.py:21` | `^CAP-[0-9A-HJKMNP-TV-Z]{26}$` |
| Contrato del transcriptor | `servicio_transcripcion/README.md` | `POST /api/transcripciones/audio` con `{id_captura, audio_base64}`; `GET /api/transcripciones/{id_trabajo}`; `id_trabajo = "tr-" + id_captura`; `x-api-key`; `MAX_BYTES_AUDIO = 4194304`; códigos 400/403/404/409/413/415/422/429/502/503/504 |
| URL e id de la clave del transcriptor | `huellita-web/samconfig.toml` | `https://289khkzbpd.execute-api.us-east-1.amazonaws.com/v1`, `IdClaveTranscriptor=14b8weklf1` |
| URL base del frontend y variables | `huellita-formato-mejorado/src/app/config.ts` | `VITE_DATOS=http` habla con el BFF en `/api`; `MAX_BYTES_AUDIO = 4 * 1024 * 1024` |
| Nombres de las funciones del frontend | `huellita-formato-mejorado/src/services/datos.ts`, `src/services/captura.ts`, `src/pages/Revisar.tsx`, `src/app/hooks.ts` | `capturar`, `guardarEvidencia`, `suscribir`, `validar`, `descartar`, `guardarSugerencias`, `marcarEvidencia`, más `procesaEnServidor` y `admiteFoto` ya declarados en la interfaz |
| Cabecera de usuaria | no existe en el frontend | la define el BFF: `X-Usuaria-Id` |
| `codigo` de error en el cliente | `huellita-formato-mejorado/src/services/errores.ts` | `ErrorParaTia(mensaje, codigo, estado)` y documenta `tope_diario` como ejemplo: por eso §4 va en minúsculas |
| Usuarias demo | `huellita-web/src/huellita_api/datos/usuarias_demo.json` | `EDU-0001` -> `SG-A`, `EDU-0002` -> `SG-B` |
| Config congelada | `huellita-web/src/huellita_api/config.py` | `Config` con `tabla_capturas`, `tabla_decisiones`, `max_capturas_dia`, `minutos_max_procesando`, `zona_horaria` y `sala_key()` |
| Modelos congelados | `huellita-web/src/huellita_api/modelos.py` | camelCase, `extra="forbid"`, `Nivel` 1..9, `ItemDecision.estado` sin `cambiada`, `DecisionesEntrada.items` 1..50 |

Diferencias con el spec, en una línea cada una:

- El script de referencia escribe `"tipo"` en `meta.json`; el spec pide tres claves y
  `ProcesarNota` lo acepta, así que manda el spec.
- `DataService.guardarSugerencias` y `marcarEvidencia` estaban marcados "fuera de alcance" en
  la versión anterior de este archivo; la tarea 6 los pone dentro (Deshacer y archivar).
- `ItemDecision` no acepta `"cambiada"`: la transición 2 de la regla 7 la deduce el servidor.
- El frontend no tiene cliente HTTP ni cabecera de usuaria: las define este contrato.

## 12. PENDIENTE DE CONFIRMAR

Estas cuatro referencias del spec (regla 5, regla 6, regla 7 y "la sección de
infraestructura") apuntan a un plan que **no está en disco**. Se buscó en
`.kiro/specs/kindergarten-observation-platform/design.md`, en `.agents/tasks/*.md`, en
`.worktrees/huellita-aws/.kiro` (no existe) y en los README del worktree.

- **Reglas 5, 6 y 7: no se encontraron.** La búsqueda de `regla 5|regla 6|regla 7` en todo el
  repositorio no devuelve nada. Lo que sí existe y las respalda parcialmente:
  - estados de Registros y su choque con los de Huellita:
    `.agents/tasks/estado-implementacion-origin-main.md:121` y `:164`;
  - `RECIBIDO -> PROCESANDO -> PROCESADO|SIN_TEXTO|ERROR`:
    `integra-backend/src/handler.py:5-8`;
  - `NO_IDENTIFICADO` como tipo de observación:
    `integra-backend/src/core/modelos.py:20`;
  - la semántica de aceptar/corregir/descartar, idéntica a la transición 1-4:
    `huellita-formato-mejorado/src/services/datos.ts` (`DataServiceLocal.validar`).
  Las versiones escritas en §8 son una **derivación propia** a partir del texto del spec y de
  esas fuentes. Hay que confirmar: (a) que `SIN_TEXTO` se muestre como `error` y no como
  `lista`; (b) que el `error` por vencimiento no se persista; (c) que la regla 5 no deba
  pisar un `ninoId` ya resuelto.
- **Sección de infraestructura: encontrada solo en forma conceptual**, no con los nombres de
  recursos. `.agents/tasks/aws-integracion-arquitectura.md:160-163` (Fase 3, "SPA en S3 +
  CloudFront") describe, en el contexto de un stack CDK para FastAPI en ECS: bucket privado
  con OAC; comportamiento por defecto hacia S3 con una CloudFront Function que reescribe a
  `/index.html` las rutas sin extensión; `/api/*` hacia el backend sin caché, con todos los
  métodos y sin reenviar el `Host` del visitante; **no** usar respuestas de error
  personalizadas para el fallback, porque aplican a toda la distribución y convertirían los
  404 y 403 de la API en `index.html`; y publicación del `dist` con `Cache-Control` inmutable
  para `assets/` y `no-cache` para `index.html`. La §10 traslada eso a SAM y a este stack
  (origen `ApiHttp` en vez de ALB) y agrega los nombres `BucketWeb`, `PoliticaBucketWeb`,
  `OacWeb`, `FuncionSpa` y `Distribucion`, que son **derivación propia** tomada de los
  nombres que pide la tarea 8. Hay que confirmar los valores de `RouteSettings`
  (`ThrottlingRateLimit: 5`, `ThrottlingBurstLimit: 10`), que son invención de este contrato.
- **Otros puntos elegidos aquí y no por el spec**, por si alguien quiere cambiarlos:
  `sugerencia_desconocida` como 422 único para ids inexistentes y del dataset;
  `TablaCapturas` con PK `id_captura` (para que el índice `porSala` que pide el spec tenga
  sentido y para poder archivar sin conocer la sala); el contador diario como ítem de la
  misma tabla, fuera del índice disperso; y `ThreadPoolExecutor` con 4 hilos para las
  consultas al transcriptor.
