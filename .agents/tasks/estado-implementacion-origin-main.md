# Estado de implementación en origin/main (BastiCan/Hackathon, 7478e89)

Revisión de solo lectura del 2026-10-15 sobre un worktree desacoplado de `origin/main` (`c:\dev\hackaton\.worktrees\revision-origin-main`). Leyenda: **[V]** verificado ejecutando (build, tests, smoke test o simulación); **[L]** inferido leyendo código o documentos.

## Resumen (pregunta 1)

- origin/main reúne tres líneas de trabajo paralelas que no se conectan y usan modelos de datos y rúbricas distintos: la app raíz (`backend/` + `frontend/`, Basti), Huellita (frontend de Flo, en dos carpetas) e `integra-backend/` (pipeline de IA en AWS, Agustín). No hay código de Cris ni de Lucas.
- La app raíz es lo único con despliegue configurado (Render vía `Dockerfile` + `render.yaml`). Funciona sobre el dataset E-1 en memoria, con IA mock heurística, sin login y sin guardar lo que se acepta. [V]
- Huellita es la interfaz más completa (agenda, sala, revisar, ficha, directora, captura foto/audio/texto), pero es una maqueta local: semilla JSON en `localStorage` e IA simulada con guiones. [V] build y 128 pruebas.
- `huellita-formato-mejorado/` es la evolución vigente de `huellita/`, que quedó congelada al cierre de la Fase 1.
- `integra-backend/` es la única pieza con IA real: texto → Bedrock (separar/identificar, conductas, RAG con Titan, clasificación ×3 con votación) → DynamoDB, disparado por S3. Tiene 97 pruebas unitarias en verde [V], pero nunca se desplegó y, tal como está, fallaría en Lambda porque busca prompts y esquemas fuera del paquete [V por simulación local].
- Ningún frontend consume `integra-backend` (no expone API) y Huellita no llama a ningún backend. No existe un flujo foto/audio → texto → clasificación → almacenamiento → ficha; no hay OCR ni Transcribe en origin/main.
- Frente a la spec de Lucas solo hay piezas de dominio reutilizables (edad, alertas, identificación por nombre, clasificación con rúbrica). Faltan captura durable con idempotencia, cola, estados de captura, corrección de transcripción y confirmación humana; `integra-backend` contradice la spec en arquitectura y en control humano.
- Integrar `lucas/kiro-specs` con origin/main no da conflictos de git: al local solo le faltan las tres carpetas nuevas (250 archivos). Los conflictos son de diseño: arquitectura, rúbrica (5 dominios × 9 niveles vs 8 núcleos × 8 niveles) y estados.

## Tabla por módulo

| Módulo | Propósito | Stack | Autor / origen | Estado |
|---|---|---|---|---|
| `backend/` + `frontend/` | App de la educadora: sala con semáforo, ficha, alertas, misión del día, captura de texto | FastAPI 0.115 + Pydantic (Python 3.13); React 18 + Vite 5 + TS; Docker + Render | BastiCan, commits directos a main del 14-oct (5325ca0, ae25558, 386ee58) | Funcional como demo; IA mock; capturas sin persistencia |
| `huellita/` | App para tías, Fase 1 (diseño post-its) | React 18 + TS + Vite + Tailwind + PWA; Vitest | Florencia Rodriguez; igual a `origin/frontend-huellita` (41dccde) | Maqueta con datos mock; versión anterior |
| `huellita-formato-mejorado/` | La misma app con diseño "agenda institucional" y correcciones | Igual (tipografía Roboto) | Florencia Rodriguez; 0010e76 y 2f58f84, solo en main | Maqueta con datos mock; versión vigente |
| `integra-backend/` | Convertir notas de texto en observaciones con nivel sugerido | Python 3.13, boto3, pydantic, jsonschema, rapidfuzz; AWS SAM: 1 Lambda, 5 tablas DynamoDB, 2 buckets S3, Bedrock | Agustín Zavala; `origin/feature/integra-backend` (PR #1 y #2) | Parcial: lógica real probada sin AWS; no desplegado; defecto de empaquetado |

## 2. Detalle por módulo (pregunta 2)

### 2.1 App raíz (`backend/` + `frontend/`)

**Implementado** [L, confirmado con smoke test]
- `backend/app/main.py`: `GET /api/health`, `/api/jardines`, `/api/jardines/{id}/salas`, `/api/salas/{jardin}/{sala}/ninos` (semáforo), `/api/salas/{jardin}/{sala}/mision`, `/api/ninos/{id}` (estado, observaciones y alertas), `/api/ninos/{id}/alertas`, `/api/ruta` y `POST /api/capturas/procesar`. También sirve `frontend/dist` con control de path traversal.
- `backend/app/data.py::DataStore` carga en memoria 6 de los 7 CSV del dataset. No carga `observacion_manifestaciones.csv`, así que ninguna vista conoce el dominio ni la manifestación de cada observación.
- `backend/app/services/analytics.py`: `edad_meses`, `nivel_esperado_para_edad`, `_clasificar_estado` (`al_dia`; `sin_evidencia` tras 4 semanas; `posible_rezago` si el nivel es menor que el esperado - 1; `ingreso_reciente`), `detectar_alertas` (sin evidencia, rezago confirmado con 2 observaciones, retroceso) y `mision_del_dia` (hasta 5 niños con "qué observar" del nivel siguiente).
- `frontend/src`: `SalaView` (selector de jardín y sala, grilla con semáforo y leyenda), `MissionCard`, `CaptureBox` y `FichaView` (alertas y línea de tiempo).

**Mock, hardcodeado o stub** [L]
- `services/ai.py::_mock_procesar`: palabras clave; identifica al niño por el número de su ID ("8" → `NINO-00008`) y sugiere el nivel esperado para la edad, no el que muestra la nota (`ai.py:113`). Cualquier otro `AI_PROVIDER` lanza `NotImplementedError` (`ai.py:151`).
- `POST /api/capturas/procesar` usa siempre la primera sala del primer jardín (`main.py:128`), no la sala elegida en la UI. `HOY = 2026-10-13` fijo (`main.py:36`).
- `CaptureBox`: solo texto; Audio y Foto son botones sin acción. "Aceptar" solo cambia el estado en pantalla (no hay endpoint para guardar) y "Cambiar" llama a la misma `aceptar(i)` (`CaptureBox.tsx:112`).
- Encabezado "Sala Caracolitos · Tía Mercedes" fijo en `App.tsx`. Sin login. El README la llama PWA, pero no hay manifest ni service worker.

**Ejecución y despliegue** [L]: local con `ver-app.bat` (requiere `backend/.venv` y `frontend/dist`) o con `uvicorn app.main:app --reload` + `npm run dev` (proxy `/api` → 8000). Render: Blueprint `integra-hackathon` (Docker, plan free, región virginia, redeploy en cada commit a main, `AI_PROVIDER=mock`, health en `/api/health`). La imagen solo lleva `backend/app`, el dataset y `frontend/dist`: Huellita e `integra-backend` no se despliegan. No verifiqué si el servicio en Render existe o está activo.

**Tests**: no hay. [V] `npm ci` + `npm run build` OK. Smoke test con `fastapi.testclient` (script temporal, borrado): los 9 endpoints responden 200; `health` = 500 niños y 2950 observaciones; 20 jardines; JAR-0001/SG-A con 13 niños (12 `sin_evidencia`, 1 `al_dia`); misión con 5 ítems; ficha de `NINO-00008` con 6 observaciones y 2 alertas; 404 para un niño inexistente. Con tres frases, `POST /api/capturas/procesar` devolvió `NINO-00008` motor_fino N9, `NINO-00051` cognitivo N8 y una frase grupal descartada.

### 2.2 `huellita-formato-mejorado/` (versión vigente)

**Implementado** [L, respaldado por las pruebas]
- Rutas (`src/app/App.tsx`): `/entrada` (usuaria de demo: tía Ana, tía Rosa o directora Carmen), `/` agenda del día por períodos de la jornada, `/sala` planilla niño × núcleo, `/revisar`, `/nino/:id`, `/directora` y `/directora/sala/:salaId` (solo lectura).
- Captura (`src/components/Captura.tsx`, `src/services/captura.ts::capturar`): foto con `capture="environment"`, reducida en el dispositivo (`lib/fotos.ts`) y guardada en `Evidencia.foto`; audio con `MediaRecorder` y tope de 60 s; texto. Devuelve el control al instante y procesa en segundo plano.
- Revisar: cita, niño, núcleo, nivel, conducta y certeza; Sí, Corregir (niño, núcleo y nivel con descriptores) y Descartar; notas de sala; "Aceptar las de certeza alta" con deshacer de 5 s; notas con error.
- Reglas puras en `src/lib/evaluacion.ts`: edad, nivel esperado, nivel actual por núcleo, nivel general (mediana), bandera "revisar avance", frescura (<14, 14-30, >30 días), "observar ahora", resumen de sala y núcleo menos cubierto.
- Directora: tarjetas por sala, mover de sala y dar de baja (en memoria). PWA con `vite-plugin-pwa` y `huellita-demo.html` (la app en un solo archivo, con las últimas correcciones [V]).

**Mock** [L]: `DataServiceLocal` (`src/services/datos.ts`) lee `data/semilla.json` (JAR-0001, salas `SALA-MMA/MMB/SCM`, 36 niños ficticios, 326 evidencias, 5 guiones de demo) y guarda en `localStorage` (`huellita:v1`). `IAServiceSimulado` (`src/services/ia.ts`) usa los guiones para foto y audio y, con texto libre, busca nombres de pila y palabras en común con la rúbrica, con 1,5 s de latencia simulada. No hay `fetch` ni SDK de AWS en `src/` [V búsqueda]. La rúbrica es propia: `data/rubrica_8_niveles.json`, 8 núcleos BCEP × 8 niveles (Comenzando a Profundizando), "propuesta del equipo" pendiente de validar con Integra.

**Ejecución**: `npm install; npm run dev`, `npm test`, `npm run build`, o doble clic en `huellita-demo.html`. Sin configuración de despliegue.

**Tests** [V]: `npm ci` + `npm run build` OK (precache de 16 entradas); `npm test`: 10 archivos, 128 pruebas en verde, igual a lo que declara `PROGRESO.md`.

**Tareas**: `.kiro/specs/app-tias/tasks.md` tiene las 14 tareas de la Fase 1 marcadas y el código las respalda (revisé componentes y pruebas de las tareas 7, 8, 9, 11, 13 y 14). `PENDIENTES.md` sigue vigente: faltan los íconos PNG de la PWA (el manifest solo usa `icono.svg`) y la cola sin conexión (requisito 1.7). Las fases 2 a 4 (Amplify/Cognito/DynamoDB, Bedrock/Transcribe, Rekognition) no empezaron.

### 2.3 `huellita/` (Fase 1)

Idéntica a `origin/frontend-huellita` (41dccde) [V `git diff` vacío]: diseño de post-its con Bricolage, Atkinson y Kalam, sin Agenda (`/` es Mi sala) y con el mismo `tasks.md` (14/14). [V] build OK y 9 archivos / 115 pruebas en verde (avisos de `act()` en stderr, sin fallos).

### 2.4 `integra-backend/`

**Implementado (código real)** [L]
- `src/core/pipeline.py::procesar_nota`: valida la entrada (`TEXTO_VACIO`, `EDUCADORA_DESCONOCIDA`, `SALA_DESCONOCIDA`); arma la nómina del jardín con `fecha_ingreso <= fecha`; llama a Bedrock con `separar_identificar`; resuelve cada sujeto con `nombres.resolver` (rapidfuzz, umbral 88, `AMBIGUO`, `FUERA_DE_SALA`, 3 candidatos); por cada particular identificado extrae conductas (`NO_EVALUABLE` con motivo), recupera candidatas por embeddings Titan (`retriever.py`, coseno sobre las 90 manifestaciones), clasifica 3 veces en paralelo con candidatas barajadas, consolida por votación (`postproceso.py`), valida que la frase de evidencia sea literal, cruza código → nivel/dominio (`rubrica.py`) y compara con la edad solo en código (`edad.py`).
- `src/core/llm.py::call_json`: Converse con tool use forzado, validación con jsonschema, 1 reintento por JSON inválido y backoff ante throttling.
- `src/handler.py` + `src/core/capturas.py`: `capturas/CAP-<ULID>/meta.json` → `Registros` en `RECIBIDO`; `texto.json` → `PROCESANDO` → `PROCESADO` (con `errores[]` por parte), `SIN_TEXTO` o `ERROR`; invocación directa para pruebas; `id_obs` determinista `{id_captura}-p{n}-{k}`.
- `src/core/datos_aws.py::DatosDynamo`: Jardines, Educadoras, Ninos, Registros (upsert), Observaciones (BatchWrite, GSI `porNino` y `porSala`) y `UpdateItem` de `Ninos.ultima_obs_fecha/ultimo_nivel`. `DatosLocal` permite correr en local con `tests/fixtures/nomina_demo.json`.
- `template.yaml`: Lambda `ProcesarNota` (Python 3.13, 300 s, 1024 MB, 2 notificaciones S3), 5 tablas on-demand, 2 buckets privados y cifrados, rol de mínimo privilegio. Scripts: `cargar_aws.py` (20 jardines, 80 educadoras, 500 niños e historial de 2950 observaciones con `origen=dataset`), `subir_captura_prueba.py`, `pipeline_local.py`, `medir.py`, `embeber_rubrica.py` y `diag_rag.py`.

**No implementado** [L]: API y frontend (fuera de alcance según `.kiro/steering/product.md`); OCR y ASR (los produciría "otro equipo"); validación de la tía; persistencia de `prompt_version`/`model_id` (las llamadas descartan `LlmMeta`, p. ej. `pipeline.py:455`, contra el requisito 8.7); `texto_extraido` en `Registros`; reglas de ciclo de vida en el bucket de capturas. Los fragmentos se procesan en serie (`pipeline.py:475`), aunque `tech.md` pide paralelo.

**Defectos**
- [V por simulación] Empaquetado Lambda: `config.RAIZ = Path(__file__).resolve().parents[2]` y `llm.PROMPTS_DIR = RAIZ / "src" / "prompts"` (`config.py:16`, `llm.py:34`). Con `CodeUri: src/` el código queda en `/var/task/core/`, así que se buscaría `/var/src/prompts`. Copié `src/` a una carpeta `task/` y `cargar_prompt` y `cargar_esquema` fallaron con `FileNotFoundError`. En AWS cada parte quedaría en `ERROR_INTERNO` y la captura en `ERROR`. Arreglo: resolver `prompts/` y `schemas/` relativo al paquete (`Path(__file__).resolve().parents[1]`).
- [L] `_actualizar_nino` (`datos_aws.py:262`) sobrescribe `ultima_obs_fecha` y `ultimo_nivel` sin condición: una captura con fecha más antigua hace retroceder el agregado, y el nivel sale de una sugerencia sin validar.
- [L] `_procesar_meta` (`handler.py:102`) fija `RECIBIDO` sin condición: si la notificación de `meta.json` se procesa después de terminar `texto.json`, el registro vuelve de `PROCESADO` a `RECIBIDO` (poco probable, posible con reintentos).
- [L] Reprocesar una captura reescribe los mismos `id_obs`; si el LLM devuelve menos observaciones, quedan filas de la corrida anterior.
- [V] `.kiro/settings/mcp.json` usa `npx @aws/aws-documentation-mcp-server`, que no existe en npm (404); el servidor oficial se publica en PyPI como `awslabs.aws-documentation-mcp-server`.

**Ejecución y despliegue** [L]: en local, con `FUENTE_DATOS=local`, `MODEL_ID_*` y credenciales para Bedrock: `scripts/pipeline_local.py --texto "..." --educadora EDU-0001 --sala SG-A --fecha 2026-10-15`. Despliegue según `docs/AWS_SETUP.md`: `sam build; sam deploy --guided` (stack `integra-procesador`), `scripts/cargar_aws.py` y prueba con `scripts/subir_captura_prueba.py` o `sam remote invoke`.

**Tests** [V]: venv con Python 3.13.14 y las dependencias de `pyproject.toml` (las guías no traen comando de instalación; las instalé por nombre). `pytest`, que excluye `-m llm` por defecto: 97 passed, 18 deselected, 7 s. `ruff check`: sin hallazgos. `cfn-lint template.yaml` (1.57.2): sin hallazgos. Todo sin credenciales AWS en el entorno; los 18 tests `llm` (Bedrock real) no se ejecutaron.

**Tareas de `tasks.md` contrastadas con el código**

| Tarea | Checkbox | Estado real |
|---|---|---|
| 1 Esqueleto | [ ] | Hecha (`pyproject.toml`, `config.py`, `modelos.py`) |
| 2 Rúbrica y few-shot | [ ] | Hecha; 8 tests, incluida la validación del few-shot contra el esquema [V] |
| 3 Dominio puro | [ ] | Hecha; tests de edad 18, nombres 9, validaciones 12 y postproceso 11 [V] |
| 4 `llm.py` | [ ] | Código hecho; su test `llm` no se ejecutó |
| 5 Embeddings y retriever | [ ] | Hecha; `embeddings_rubrica.json` versionado; 6 tests sin AWS [V] |
| 6 Pipeline | [ ] | Código hecho; los 13 casos de `tests/llm` no se ejecutaron |
| 7 `medir.py` | [ ] | Script hecho; sin reporte versionado (`data/eval/` está en `.gitignore`): no hay evidencia de accuracy |
| 7b Checkpoint de calidad | [ ] | Sin evidencia |
| 8 AWS | [ ] | Código hecho; template sin hallazgos de lint [V]; no desplegado |
| 8b a 8f | [x] | Hechas; tests de capturas 16, datos_aws 6 y handler_s3 11 [V] |
| 9 Despliegue y prueba | [ ] | Pendiente; fallaría por el defecto de rutas |

## 3. `huellita/` vs `huellita-formato-mejorado/` (pregunta 3)

- Es una evolución. Historia: e6f6922 (Fase 1) → 41dccde (cierre de la Fase 1, `origin/frontend-huellita`) → 0010e76 (diseño v2 editado dentro de `huellita/`) → 2f58f84 (mueve la v2 a `huellita-formato-mejorado/` con correcciones y devuelve `huellita/` al estado de 41dccde).
- Vigente: `huellita-formato-mejorado/`. Es la más reciente, tiene más pruebas (128 vs 115) y su README y `.kiro/steering/diseno-visual.md` marcan el diseño anterior como histórico ("no seguirlo").
- Diff (`git diff origin/main:huellita origin/main:huellita-formato-mejorado`): 57 archivos, +1936/-1041. Agrega la Agenda como inicio (`pages/Agenda.tsx`, `lib/agenda.ts`), encabezado institucional, miniaturas y foto del post-it guardada (`Miniatura.tsx`, `lib/fotos.ts`), colores por ámbito (`ambitos.ts`) y fotos de post-its de demo. Quita `Escalera` y `TarjetaNino`. Cambia la tipografía a Roboto, Mi sala a planilla, la ficha a vista por ámbito, Revisar a orden de llegada, "Cambiar" a "Corregir" y el mensaje de días futuros. Las interfaces `DataService`/`IAService` y las reglas de `evaluacion.ts` se mantienen, salvo el campo nuevo `Evidencia.foto`.
- [L] Ambas usan la clave `localStorage` `huellita:v1` y semilla `version: 1`: abiertas en el mismo origen (p. ej. `localhost:5173`), una carga el estado guardado por la otra.

## 4. Integración (pregunta 4)

- Solo `frontend/` consume una API: `frontend/src/api.ts` llama a `/api/*` de `backend/`. Huellita no hace llamadas de red e `integra-backend` no expone HTTP (solo eventos S3 e invocación directa de la Lambda). [V búsqueda + L]
- Contratos actuales, incompatibles entre sí:

| | App raíz | Huellita | integra-backend |
|---|---|---|---|
| Rúbrica | 5 dominios × 9 niveles (dataset) | 8 núcleos BCEP × 8 niveles | 5 dominios × 9 niveles, 90 códigos |
| Niños | IDs del dataset, sin nombre | 36 ficticios con nombre en salas `SALA-*` | Dataset + nombres de demo para los 26 niños de JAR-0001 |
| Sugerencia | `SugerenciaIA` (id_nino_sugerido, dominio, nivel_sugerido, manifestacion_sugerida, certeza, evidencia) | `Sugerencia` (ninoId, nucleo, nivel, conducta, cita, certeza, estado) | `Observacion` (tipo, id_nino, manifestaciones[], nivel, certeza, comentario, comparacion_edad, candidatos) |
| Estados | Ninguno | Evidencia `procesando/lista/error`; sugerencia `pendiente/aceptada/cambiada/descartada` | `Registros` `RECIBIDO/PROCESANDO/PROCESADO/SIN_TEXTO/ERROR`; observación `SUGERIDO` |
| Transporte | REST síncrono | Interfaces TypeScript locales | S3 `meta.json` + `texto.json` → Lambda → DynamoDB |

- Flujos que funcionan hoy:
  1. App raíz: texto → IA mock → sugerencias en pantalla, sin guardar; sala, ficha y alertas sobre el dataset. [V local]
  2. Huellita: foto, audio o texto → IA simulada → Revisar → aceptar o corregir → sala y ficha actualizadas, todo en el navegador. [V con `src/app/demo.test.tsx`; no lo recorrí en un navegador]
  3. `integra-backend`: texto → Bedrock → DynamoDB. Verificado solo con dobles de prueba; en local requiere credenciales y en Lambda falla por el defecto de rutas.
- Desconectado: foto → OCR y audio → Transcribe (no existen); quién escribe `meta.json` y `texto.json` en S3 (solo `subir_captura_prueba.py`); lectura de `Registros`/`Observaciones` desde un frontend; validación persistida de la tía; un adaptador de `DataService`/`IAService` hacia un backend real.

## 5. Cobertura frente a la spec de Lucas (pregunta 5)

Referencia: `.kiro/specs/kindergarten-observation-platform/design.md` (solo existe el diseño; no hay requirements ni tasks).

| Elemento de la spec | Estado | Evidencia en origin/main |
|---|---|---|
| C1 Sesión, roles, PIN de demo, alcance por sala | Parcial (maqueta) | Huellita `/entrada` con roles `tia`/`directora` en `localStorage`; sin PIN, token ni API. Raíz e integra-backend sin autenticación |
| C2 Vista de sala (`nombre_pila`, icono/color, semáforo, insignias) | Parcial | Raíz `GET /api/salas/.../ninos` con IDs y estados propios; Huellita planilla con nombres. Sin icono/color de desambiguación ni insignias |
| C3 `POST /api/capturas` con `Idempotency-Key`, 202 durable, 422 para video | No implementado | Raíz: `POST /api/capturas/procesar` síncrono, solo texto. Huellita: captura local |
| C3 Audio de 300 s (mínimo 240 s), `timeslice`, Wake Lock, selector de archivo | Contradice | Huellita corta a los 60 s (`Captura.tsx:6`), sin `timeslice` ni Wake Lock |
| C4 Transcribe por lotes, confianza por palabra, idioma | No implementado | Nada en origin/main |
| C4 Bedrock desde texto | Parcial | `integra-backend/src/core/pipeline.py`; no desplegado |
| C4 Bedrock desde foto | No implementado | |
| C5 Ficha, historial, guía de 10 manifestaciones, recomendación de 5 áreas | Parcial | Raíz `FichaView` (sin dominio); Huellita ficha por núcleo y "Observar ahora"; sin guía ni recomendador |
| C6 Directora | Parcial (maqueta) | Huellita `/directora` |
| C7 Bandeja de capturas en curso, demorada, polling de 30 s | No implementado | Huellita "Revisar" lista sugerencias locales; `Registros` de integra-backend no tiene API |
| C8 Nombre de pila, aviso de envío a AWS, miniaturas ocultas | Parcial | Huellita usa nombre de pila e iniciales; no avisa de AWS (no envía nada) y muestra las fotos de post-its sin ocultarlas |
| C9 Sincronización con IndexedDB | No implementado | Huellita usa `localStorage`; la cola sin conexión figura en `PENDIENTES.md` |
| C10 Trabajador durable (PostgreSQL, arrendamiento, máximo 3) | No implementado | integra-backend usa Lambda por evento S3, sin cola |
| Modelo PostgreSQL y extensiones (`captura`, `cola_procesamiento`, `sugerencia_ia`, `observacion_meta`, `nino_app`...) | No implementado | Raíz: CSV en memoria; integra-backend: 5 tablas DynamoDB |
| Siembra 20/80/500/9/90/2950/8850 | Parcial | Raíz carga 20/80/500/9/90/2950 [V], no los 8850 vínculos; `cargar_aws.py` sí los usa (no ejecutado) |
| Alg. 1 Edad y niveles compatibles (P16 contra `consolidado.json`) | Parcial | Misma fórmula en `analytics.edad_meses` y `edad.py` (18 tests [V]); ningún test compara con `consolidado.json` |
| Alg. 2 Semáforo con insignias que no cambian el color | Divergente | La raíz pinta `posible_rezago` e `ingreso_reciente` como colores (sigue la §6.1 de la síntesis, que la spec reemplaza); Huellita usa frescura de 14/30 días |
| Alg. 3 Aceptación, sincronización y trabajo | No implementado | |
| Alg. 4 Candidatos por nombre, homónimos sin autoasignar | Parcial | `integra-backend/src/core/nombres.py` (`AMBIGUO` + candidatos, 9 tests [V]); sin UI de selección |
| Alg. 5 Sugerencia (nivel 1-9, 1-5 manifestaciones del nivel, nota y fragmento ≤ 280) | Parcial | integra-backend: hasta 3 códigos, sin validar que sean del mismo nivel (manda el de mayor certeza); frase literal validada; sin límite de 280 |
| Alg. 6 Corrección de transcripción y confirmación idempotente | No implementado | Huellita confirma y corrige sugerencias solo en el navegador |
| Alg. 7 Recomendador y guía | Parcial | `mision_del_dia` (raíz) y "Observar ahora" (Huellita) |
| Alg. 8 Traslado y baja con auditoría | Parcial (maqueta) | Huellita `moverNino`/`darDeBaja` en memoria, sin auditoría |
| Retención de hasta 24 h y purga | No implementado | `template.yaml` sin reglas de ciclo de vida |

**Contradicciones con lo implementado**
1. Arquitectura: la spec define FastAPI + PostgreSQL + trabajador y dice que no se requieren Lambda, SAM ni API Gateway. `integra-backend` es Lambda + SAM + DynamoDB disparada por S3, y su `product.md` deja fuera API, frontend y validación.
2. Flujo S3 y frontera AWS (P21): en la spec solo FastAPI escribe en S3 y llama a Transcribe/Bedrock; `integra-backend` espera que un tercero deje `meta.json` y `texto.json` directo en el bucket.
3. Estados de captura: la spec usa `recibida`, `subiendo`, `en_cola`, `transcribiendo`, `procesando`, `lista_para_revisar`, `pendiente_asignacion`, `revision_manual`, `confirmada` y `descartada`; `integra-backend` usa `RECIBIDO`, `PROCESANDO`, `PROCESADO`, `SIN_TEXTO` y `ERROR`. No hay estados de revisión, asignación pendiente ni confirmación, y la spec no contempla un `PROCESADO` con errores parciales.
4. Control humano (P8): la spec solo permite crear observaciones con `confirmarCaptura`. `integra-backend` guarda las sugerencias en la tabla `Observaciones` (estado `SUGERIDO`, junto al historial del dataset) y actualiza `Ninos.ultimo_nivel` sin validación.
5. Idempotencia: la spec usa `Idempotency-Key` en la aceptación y confirmación idempotente con bloqueo de fila. `integra-backend` solo tiene `id_obs` determinista y upserts sin condición (ver carreras en §2.4).
6. Corrección de transcripción: sin equivalente. No se guarda la transcripción ni sus versiones (`texto.json` es la entrada final) y no existen el paso a `en_cola` ni el 409.
7. Rúbrica: la spec (D3, núcleo = dominio) y el dataset usan 5 dominios × 9 niveles; Huellita usa 8 núcleos × 8 niveles BCEP.
8. Audio: la spec pide mínimo 240 s (300 por defecto); Huellita corta a los 60 s, como pide su propio `requirements.md` (1.3).

**Reutilizable**: fórmula de edad; la edad no llega al LLM; frase literal de respaldo validada; certeza alta/media/baja por votación; homónimos → `NO_IDENTIFICADO` con candidatos; IDs `CAP-<ULID>`; rúbrica como configuración (`rubrica.json`). Por autor, origin/main cubre en parte el reparto de la spec: Basti (sala), Flo (captura y experiencia) y Agustín (IA y AWS); no hay código de Cris ni de Lucas.

## 6. Cobertura frente al desafío (pregunta 6)

Imprescindibles de `Dump/integra_desafio1_sintesis.md` §9:

| Imprescindible | Estado en origin/main |
|---|---|
| Captura de audio y foto | Solo UI local (Huellita); nada convierte foto o audio a texto |
| IA: separar, identificar y sugerir nivel con evidencia | Real en integra-backend (no desplegado); mock en la raíz; simulada en Huellita |
| Bandeja para aceptar o cambiar | Huellita (local); en la raíz no persiste |
| Vista de sala con semáforo | Raíz (dataset) y Huellita (semilla) |
| Ficha con línea de tiempo por núcleo | Huellita por núcleo; la raíz no conoce el núcleo |
| Las dos alertas | Raíz `detectar_alertas`; Huellita frescura y "revisar avance" |
| Misión del día | Raíz `mision_del_dia` y `MissionCard`; Huellita "Observar ahora" en la ficha |

De lo "si alcanza": la vista de directora y el mapa de cobertura (planilla niño × núcleo) existen como maqueta en Huellita; integra-backend no envía al LLM el `id_nino` ni la edad, pero sí nombres de pila; no hay borrado automático de archivos. Ningún módulo mide el KPI de horas (`medir.py` mide accuracy, no tiempo). `Dump/Rubrica_DIAEP.pdf` (Agencia de Calidad 2025, 148 páginas, Niveles de Transición, organizada por núcleo y OA con niveles de progreso como Comenzando, Desarrollando, Consolidando y Profundizando) no se usa en ningún módulo; cubre 4 a 6 años, mientras la ruta del dataset llega a 36 meses.

## 7. Working tree local y rama `lucas/kiro-specs` (pregunta 7)

- `lucas/kiro-specs` (d9deb26) = 386ee58 + 4 commits que solo agregan `.kiro/specs/kindergarten-observation-platform/design.md` (1122 líneas). Está 25 commits detrás de origin/main; `main` local también, y avanza por fast-forward.
- Al working tree local le faltan exactamente `huellita/` (79 archivos), `huellita-formato-mejorado/` (87) e `integra-backend/` (84). Fuera de esas carpetas origin/main no cambió nada respecto de 386ee58 [V `git diff` vacío]: la app raíz, `Dump/` y `.gitignore` son iguales.
- `git merge-tree --write-tree lucas/kiro-specs origin/main` termina sin conflictos (árbol 19c0a5bd) [V]. No hay rutas compartidas: los `.kiro/` de origin/main están solo dentro de las tres subcarpetas.
- Cambios sin commitear: origin/main no toca `.gitignore` (el local agrega `.kiro/settings/mcp.json` y `.worktrees/`), así que no bloquea un merge; `.agents/`, `.kiro/steering/` y `.config.kiro` no chocan con rutas de origin/main.
- Durante la revisión apareció en el working tree la carpeta no trackeada `servicio_transcripcion/` (archivos de 10:50 a 11:03, con `contrato/resultado_transcripcion.schema.json` y `src/transcriptor/`). No la creó esta revisión, no está en ninguna rama remota y no la analicé.
- Conflictos semánticos, no de git: (a) abrir Kiro en la raíz carga solo el steering de Lucas (`aws-agent-rules.md`; `equipo.md` está vacío), y el steering de cada subproyecto solo aplica al abrir su carpeta; (b) `integra-backend/.kiro/steering/product.md` pide no usar `backend/` ni `frontend/` como referencia, y la spec de Lucas declara que la implementación existente no restringe su arquitectura; (c) el patrón `.kiro/settings/mcp.json` del `.gitignore` local está anclado a la raíz y no afecta a `integra-backend/.kiro/settings/mcp.json`, ya versionado y sin secretos; (d) tres diseños con arquitectura, rúbrica y estados distintos (§5).

## 8. Gaps, riesgos y próximos pasos (pregunta 8)

**Riesgos principales**
1. Tres stacks sin contrato común: hoy no hay una demo con flujo real de punta a punta.
2. Rúbrica sin decidir: dataset 5 × 9, Huellita 8 × 8, DIAEP de transición.
3. integra-backend sin desplegar, con un defecto que bloquea la Lambda y sin evidencia versionada de accuracy ni de los tests `llm`.
4. No existe conversión de foto o audio a texto.
5. La IA escribe observaciones y agregados sin validación humana (integra-backend).
6. La app raíz se publica en Render sin autenticación; aceptable solo con datos sintéticos, como advierte su README.
7. Huellita duplicada y con estado `localStorage` compartido entre versiones.

**Próximos pasos sugeridos**
1. Decidir en equipo la arquitectura objetivo (spec de Lucas o Lambda de integra-backend) y una rúbrica única, o un mapeo explícito núcleo ↔ dominio.
2. En integra-backend: corregir las rutas de `prompts/` y `schemas/`, correr el checkpoint 7b (`medir.py` y los 13 casos) y desplegar (tarea 9).
3. Acordar el contrato frontend-backend sobre `DataService`/`IAService` de `huellita-formato-mejorado` (`Observacion` → `Sugerencia`, `GENERAL` → nota de sala, `NO_IDENTIFICADO` → "por confirmar") y exponer una API delgada que suba `meta.json`/`texto.json` y lea `Registros`/`Observaciones`.
4. Agregar el productor de `texto.json`: Transcribe para audio y Bedrock con visión para fotos.
5. Persistir la validación de la tía antes de actualizar `ultimo_nivel` y guardar `llm_meta`.
6. Integrar la rama local (merge limpio; el `.gitignore` local no interfiere) y evaluar retirar la carpeta `huellita/` duplicada.

## Método y alcance

- Worktree desacoplado en 7478e89 (`c:\dev\hackaton\.worktrees\revision-origin-main`; queda creado). En `c:\dev\hackaton` solo escribí este informe.
- Python 3.13.14 con venvs dentro del worktree. Node 22.22.2 (el de Kiro; el Dockerfile usa Node 24). `npm` no estaba en el PATH: descargué npm 10.9.9 de registry.npmjs.org dentro del worktree, verifiqué su SHA-1 contra el registro, lo usé con caché local y lo borré al terminar. Instalé `cfn-lint` y `pypdf` en el venv del worktree para el lint del template y para leer el índice del PDF DIAEP.
- Sin llamadas a AWS ni Bedrock: tests sin credenciales en el entorno y con la metadata EC2 deshabilitada. No ejecuté los tests `llm`, no verifiqué Render y no recorrí Huellita en un navegador.
- Temporales borrados (smoke test, npm, caché y simulación Lambda). Dentro del worktree quedan `.venv`, `node_modules` y `dist`, ignorados por git.
