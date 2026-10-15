# Integración de la arquitectura AWS propuesta con el repositorio actual

Revisión de solo lectura del 15-10-2026 sobre `c:\dev\hackaton` (rama `lucas/kiro-specs`, d9deb26) y el worktree `.worktrees/revision-origin-main` (`origin/main`, 7478e89). No se editó, instaló, construyó ni ejecutó nada del proyecto; este informe es el único archivo creado. Las citas `ruta:línea` sin prefijo son del checkout principal; las marcadas `origin/main:` se leyeron en el worktree.

Leyenda: [V] verificado leyendo código o documentación AWS · [I] inferencia · [PV] por verificar.

## Resumen

- Lo que hoy se despliega es una demo de solo lectura: FastAPI carga 6 CSV en memoria y no escribe nada; la única IA es un mock heurístico, síncrono y solo de texto. En `backend/` y `frontend/` no hay base de datos, S3, cola, autenticación, tests ni CI [V].
- La imagen Docker actual sirve tal cual para la Fase 0: corre sin root, escucha en `PORT` (8000 por defecto), expone `/api/health` sin dependencias externas y FastAPI ya hace el fallback del SPA. En Express Mode basta fijar `ContainerPort` 8000 y `HealthCheckPath` `/api/health` [V].
- La abstracción de IA es una sola función síncrona de texto (`ai.procesar_captura`) con rama `mock`; `AI_PROVIDER=bedrock` hoy termina en `NotImplementedError` (HTTP 500). Sirve para enchufar Bedrock en la Fase 1, pero no para el flujo 202 asíncrono del spec [V].
- Ya existe código AWS reutilizable fuera de `backend/`: `origin/main:integra-backend/` (Bedrock Converse con tool use forzado y un pipeline de clasificación medido, sobre SAM, Lambda y DynamoDB) y `servicio_transcripcion/` (sin versionar y en edición durante esta revisión: Transcribe por lotes detrás de Mangum). Ambos apuntan a Lambda, que el spec y la propuesta descartan; su lógica se puede mover al trabajador [V].
- `huellita/` y `huellita-formato-mejorado/` (solo en `origin/main`) son otra app, no una versión de `frontend/`: PWA con foto y MediaRecorder, datos en `localStorage`, sin llamadas HTTP y con una rúbrica de 8 núcleos × 8 niveles, distinta del dataset E-1 (5 dominios × 9 niveles). Qué frontend se despliega queda como decisión pendiente [V].
- Verificado en documentación AWS: el puerto es `PrimaryContainer.ContainerPort` (por defecto 80); un servicio ECS estándar puede compartir el cluster de un servicio Express; `aws-cdk-lib` expone `aws_ecs.CfnExpressGatewayService`, solo como L1 [V].
- Conflicto de costos: Aurora no se pausa mientras haya conexiones de usuario abiertas, y un trabajador que sondea la cola las mantiene. Además la reanudación (~15 s) supera el timeout de 5 s del health check del ALB, así que `/api/health` nunca debe tocar la base [V].
- El hackathon es del 14 al 16 de octubre (README.md:6) y hoy es 15-10: lo alcanzable antes de la demo es Fase 0 + Fase 1. La Fase 2 (Aurora, cola, trabajador, IndexedDB) es de esfuerzo L [I].

## 1. Estado actual

### 1.1 Ramas y archivos fuera de git

- El checkout está en `lucas/kiro-specs`: 4 commits sobre `main` local (386ee58) que solo agregan `.kiro/specs/kindergarten-observation-platform/design.md`, y 25 commits detrás de `origin/main` (`git rev-list --left-right --count HEAD...origin/main` = 4/25) [V].
- `backend/`, `frontend/`, `Dockerfile`, `render.yaml`, `README.md`, `.dockerignore` y `ver-app.bat` son idénticos en HEAD y `origin/main`; `origin/main` agrega `huellita/`, `huellita-formato-mejorado/` e `integra-backend/` (PR #1 y #2; las ramas `origin/frontend-huellita` y `origin/feature/integra-backend` ya están fusionadas) [V]. `design.md` no está en `origin/main` [V].
- Sin versionar en el checkout: cambio en `.gitignore` (líneas 42-45: ignora `.kiro/settings/mcp.json` y `.worktrees/`), `.agents/`, `.kiro/steering/`, `.config.kiro` del spec y `servicio_transcripcion/`, que apareció durante la revisión (archivos con hora 10:50 a 11:03) [V]. El worktree tiene `.herramientas/` sin versionar (tarball de npm 10.9.9 y su caché) [V].
- No hay `.github/`, `buildspec`, `samconfig` ni CDK en ninguna de las ramas revisadas [V].

### 1.2 Backend (`backend/`)

| Ruta | Línea | Comportamiento |
|---|---|---|
| `GET /api/health` | main.py:52 | Devuelve estado y conteos; carga el dataset en memoria; no toca servicios externos |
| `GET /api/jardines`, `/api/jardines/{id}/salas` | main.py:62, 68 | Lectura del store |
| `GET /api/salas/{jardin}/{sala}/ninos`, `/mision` | main.py:77, 86 | Semáforo y misión vía `analytics` |
| `GET /api/ninos/{id}`, `/alertas` | main.py:92, 108 | Ficha, trayectoria y alertas |
| `GET /api/ruta` | main.py:117 | Ruta de niveles |
| `POST /api/capturas/procesar` | main.py:123 | Síncrono, solo texto (`CapturaRequest`, models.py:101); usa siempre la primera sala del primer jardín como roster (main.py:128-130) |
| `GET /{ruta:path}` | main.py:142 | Fallback SPA solo si existe `frontend/dist/index.html` (:140); `/api/*` inexistente responde 404 (:145); evita path traversal (:154); `assets/` con caché inmutable (:158); asset inexistente 404 (:163); resto, `index.html` sin caché (:167). No usa `StaticFiles` |

- Datos: `DataStore` en memoria con `csv.DictReader` (data.py:26, 33); carga jardines, educadoras, niños, ruta, manifestaciones y observaciones (data.py:53-99); no carga `observacion_manifestaciones.csv` ni `consolidado.json`; singleton con `lru_cache` (data.py:135). No hay escrituras ni base de datos: "Aceptar" en la UI solo cambia estado local (CaptureBox.tsx:105-115) [V].
- Configuración (solo nombres): `DATASET_DIR`, `FRONTEND_DIST`, `AI_PROVIDER` (config.py:23-29; .env.example:4, 7, 10) y `PORT` (Dockerfile:33). Constantes `WEEKS_WITHOUT_EVIDENCE` y `MIN_OBS_TO_CONFIRM` (config.py:33, 35). La fecha de referencia está fija: `HOY = 2026-10-13` (main.py:36) [V].
- IA: `services/ai.py` solo implementa `mock` (:148); hay un comentario reservando la rama `bedrock` (:150) y cualquier otro valor lanza `NotImplementedError` (:151-152). Identifica niños por el sufijo numérico del ID (:65-77) porque el dataset no tiene nombres. No hay boto3, Bedrock ni Transcribe, ni manejo de credenciales [V].
- CORS: solo `http://localhost:5173` y `http://127.0.0.1:5173` (main.py:44-49), para el servidor de Vite; desplegado, todo es mismo origen [V].
- `/docs` y `/openapi.json` quedan públicos (FastAPI por defecto, main.py:38-42) [V].
- Dependencias fijadas: fastapi 0.115.5, uvicorn[standard] 0.32.1, pydantic 2.10.3, python-multipart 0.0.17 (requirements.txt:1-4). Sin boto3, driver PostgreSQL, migraciones ni pytest [V].
- `services/analytics.py` son funciones puras sobre el store (`edad_meses` :17, `estado_nino` :47, `detectar_alertas` :94, `mision_del_dia` :172): siguen sirviendo si el store conserva su interfaz [I].

### 1.3 Frontend (`frontend/`)

- `api.ts` usa `fetch` con rutas relativas `/api/...` (api.ts:11-36); no hay `VITE_*` ni `import.meta.env`. En desarrollo, Vite hace proxy de `/api` a `localhost:8000` (vite.config.ts:8-14). Esto ya calza con mismo dominio, sea imagen única o CloudFront con `/api/*` [V].
- `CaptureBox`: los botones Audio, Foto y Texto no tienen acción (CaptureBox.tsx:42-50); solo hay un textarea y "Procesar con IA" (:53-61). No recibe la sala (SalaView.tsx:68) [V].
- No hay IndexedDB, service worker, manifest, MediaRecorder ni `getUserMedia`; `index.html` solo tiene `theme-color` (index.html:7). El README la llama PWA (README.md:29), pero hoy no lo es [V].
- React 18 y react-router 6 con `BrowserRouter` (main.tsx:9; rutas en App.tsx:16-19), así que necesita fallback SPA; el encabezado está fijo (App.tsx:10). `package.json` no tiene script de test (:6-10); usa rangos `^`, pero el build es reproducible con `package-lock.json` y `npm ci` (Dockerfile:7) [V].

### 1.4 Despliegue y ejecución local

- Dockerfile: etapa `node:24-alpine` que compila el frontend (:4-9) y etapa `python:3.13-slim` (:12-33) con usuario uid 10001 (:27-28), `WORKDIR /srv/backend` (:30), `EXPOSE 8000` (:31) y `uvicorn` en `${PORT:-8000}` (:33). `REPO_ROOT` resuelve a `/srv` (config.py:12) y calza con los `COPY` (:22-24) [V].
- `.dockerignore` (:2-11) no excluye `.worktrees/`: el contexto de build incluye la copia completa de `origin/main` y su caché de npm. Tampoco excluirá un futuro `infra/cdk.out` [V/I].
- `render.yaml`: servicio Docker, plan free, región virginia, `healthCheckPath /api/health`, autodeploy por commit, `AI_PROVIDER=mock` (:4-17). El README avisa que el servicio se duerme a los 15 min (README.md:50) y que no hay login (README.md:52) [V].
- `ver-app.bat` corre `uvicorn` en 127.0.0.1:8000 con `backend\.venv` y `frontend\dist`; no usa Docker [V].
- Tests y CI: ninguno en `backend/` ni `frontend/`. En `origin/main` hay pytest en `integra-backend/tests/{unit,llm}` (las `llm` no corren por defecto) y vitest en `huellita*/src` [V].

### 1.5 Código AWS y frontends fuera de `backend/` y `frontend/`

`origin/main:integra-backend/` (otro backend, no comparte código con `backend/`):
- SAM con 1 Lambda disparada por S3, 5 tablas DynamoDB, 2 buckets y un rol (template.yaml:1-6, 187-230); bucket de capturas con nombre fijo `integra-capturas-<cuenta>` (template.yaml:175).
- `llm.py`: Converse con tool use forzado, validación jsonschema y backoff (`_converse` :153, `call_json` :198); cliente con la cadena estándar de boto3 (:116). Pipeline separar → conductas → RAG con Titan → clasificar 3 veces (`procesar_nota`, pipeline.py:397). Interfaz `Datos` de 4 métodos (datos.py:23-37). Variables `FUENTE_DATOS`, `MODEL_ID_*`, `TABLA_*`, `BUCKET*` (config.py:60-72).
- Credenciales: rol de Lambda en AWS; en local, credenciales temporales del evento pegadas en la terminal (AWS_SETUP.md §1; `.env.example:3-5` solo trae los nombres).
- Reutilizable como librería del trabajador con una implementación PostgreSQL de `Datos`. Choca con el spec en un punto: `guardar_observaciones` crea observaciones en estado `SUGERIDO` (pipeline.py:489, modelos.py:209); en el spec eso es `sugerencia_ia` y solo confirmar crea observaciones. Su guía pide no reutilizar `backend/` (LEEME_KIRO.md:44) y D1 (DynamoDB), D2 (Lambda) y D5 (SAM) siguen "por discutir" (DECISIONES.md:8-12).

`servicio_transcripcion/` (sin versionar, en edición; las líneas pueden moverse):
- FastAPI + Mangum para API Gateway REST: `POST /api/transcripciones/audio` (202), `GET /api/transcripciones/{id}` y `GET /api/salud` (app.py:96-130); handler de EventBridge al terminar el trabajo (eventos.py).
- `ServicioTranscribe.iniciar` sube el audio a `audio/…` y llama a `StartTranscriptionJob` con `OutputBucketName` y `OutputKey` `transcripciones/…` (servicio.py:60-92); tiene `ServicioMock` (:224).
- Variables `BUCKET`, `TRANSCRIBE_IDIOMA` (es-US, es-MX, es-ES), `UMBRAL_PALABRA_DUDOSA` (0.60), `MAX_BYTES_AUDIO` (4 MB por el límite de 6 MB de Lambda), `PREFIJO_TRABAJO`, `MODO_MOCK` (config.py:24-29).
- Reutilizable como adaptador de Transcribe del trabajador, sin Mangum. El tope de 4 MB deja de aplicar (la API sube a S3) y hay que alinear versiones (fastapi 0.143.1 frente a 0.115.5). Confirmar con su autor antes de moverlo.

`origin/main:huellita/` y `huellita-formato-mejorado/` (v2 de la misma app):
- React + Tailwind + `vite-plugin-pwa` (vite.config.ts:9; `navigateFallbackDenylist` para `/api/` en :37, compatible con CloudFront `/api/*`). Interfaces `DataService` (datos.ts:41) e `IAService` (ia.ts:35) con implementación local en `localStorage` (`huellita:v1`, datos.ts:22).
- Foto con `capture="environment"` (Captura.tsx:45), audio con MediaRecorder (Captura.tsx:114-120) y reducción de fotos en el dispositivo (`reducirFoto`, fotos.ts:27). No persiste archivos ni tiene cola sin conexión (PENDIENTES.md, ítems 2 y 8).
- Planea su propio backend con Amplify, Cognito y DynamoDB (README.md:20-23) y se declara "solo frontend" (tecnologia.md:11). Usa una rúbrica de 8 núcleos × 8 niveles BCEP (README.md:14) y una semilla propia de 36 niños (README.md:16).

### 1.6 Spec

`design.md` declara ilustrativa la implementación actual (:5) y fija FastAPI + PostgreSQL + trabajador (D9, :47), Transcribe por lotes + Bedrock (D10, :48), concurrencia 3 (D11, :49), audio hasta 300 s y nunca menos de 240 s (D12, :50), sin Lambda, SAM ni API Gateway (:56), purga hasta 24 h después del estado terminal (:625), frontera AWS solo en backend (:954) y H0 = verificar permisos primero (:1072). El hallazgo de `design-review.md` (corrección sin cambio de estado) ya está resuelto en la versión actual: el Algoritmo 6 pasa la captura a `en_cola` [V].

## 2. Brechas

| Componente | Estado | Evidencia |
|---|---|---|
| Contenedor en ECS Express Mode | Falta | Solo Render (render.yaml:4-17); no hay IaC para `backend/` |
| Imagen apta para ECS | Existe | Dockerfile:12-33 (sin root, `PORT`, 8000) |
| Health check | Existe | main.py:52, sin dependencias externas |
| SPA servida por la API con fallback | Existe | main.py:138-167 |
| SPA en S3 + CloudFront con `/api/*` | Falta, sin bloqueos | Rutas relativas (api.ts:11-36), sin `VITE_*` |
| Captura asíncrona 202 con `Idempotency-Key` | Falta | Solo `POST /api/capturas/procesar` síncrono (main.py:123) |
| Captura de foto y audio | Falta en `frontend/`; existe en huellita | CaptureBox.tsx:42-50; huellita Captura.tsx:45, 114-120 |
| IndexedDB y espera de conectividad | Falta | Sin resultados en `frontend/`; huellita usa `localStorage` (datos.ts:22) |
| PWA | Falta en `frontend/`; existe en huellita | index.html:7; huellita vite.config.ts:9 |
| PostgreSQL (dominio, capturas, idempotencia) | Falta | data.py:33-131 en memoria; requirements.txt sin driver |
| Siembra 20/80/500/9/90/2950/8850 | Parcial | 6 de 7 CSV en memoria (data.py:53-99); falta `observacion_manifestaciones` |
| Cola durable y trabajador (concurrencia 3) | Falta | Ninguno; integra-backend procesa dentro de la Lambda disparada por S3 (template.yaml:209-230) |
| S3 privado | Falta en `backend/`; existe en SAM | origin/main:integra-backend/template.yaml:158-185 |
| Transcribe por lotes | Falta en `backend/`; existe sin versionar | servicio_transcripcion servicio.py:60-92 |
| Bedrock (texto, foto, transcripción) | Falta en `backend/`; existe para texto en integra-backend | ai.py:148-153; llm.py:153-226 |
| Credenciales por rol, sin claves | Parcial | `backend/` no usa AWS; integra-backend usa el rol de Lambda (llm.py:116) |
| Secrets Manager | Falta | Nada en ninguna rama |
| VPC y Aurora | Falta | Nada en ninguna rama |
| IAM de mínimo privilegio para ECS | Falta | Solo la política de la Lambda (template.yaml:236-293); incluye `bedrock:Converse`, que sobra porque Converse se autoriza con `bedrock:InvokeModel` |
| Logs, alarmas y métrica de la cola | Falta | Solo logs de uvicorn por stdout |
| Autenticación y alcance por jardín y sala | Falta | README.md:52; los endpoints aceptan cualquier ID (main.py:68-120) |
| Nombres de pila (D6) | Falta | ai.py:65-77 identifica por sufijo del ID |
| Retención y purga | Falta | Nada en `backend/` |
| Tests y CI | Falta | Sin tests en `backend/` ni `frontend/`; sin `.github` |
| IaC | Parcial | SAM en integra-backend; nada en CDK |

## 3. Plan por fases

| Fase | Objetivo | Esfuerzo | ¿Antes de la demo? |
|---|---|---|---|
| 0 | Imagen actual en ECS Express Mode | S | Sí |
| 1 | IA real con task role (S3, Transcribe, Bedrock) | M | Sí |
| 2 | Aurora, siembra, idempotencia, cola y trabajador | L | Solo si sobra tiempo |
| 3 | SPA en S3 + CloudFront | M | No es necesaria |
| 4 | Cognito, secretos, alarmas, CI con OIDC | M-L | No |

Precondición (H0 del spec, design.md:1072): confirmar que la cuenta del evento permite crear roles IAM y roles vinculados a servicios, ejecutar `cdk bootstrap`, usar ECS Express Mode, Aurora, Transcribe y el modelo de Bedrock elegido (incluido el formulario de Anthropic si aplica, AWS_SETUP.md §2). Las credenciales del evento son temporales (AWS_SETUP.md §1); si IAM está restringido, cambia todo el plan [PV].

### Fase 0: imagen actual en Express Mode (reemplaza a Render) · S

- Archivos: nuevo `infra/` (app CDK en Python con `RedStack` y `AppStack` mínimos, ver sección 6); `.dockerignore` agrega `.worktrees/`, `.agents/`, `infra/`, `**/cdk.out` y `servicio_transcripcion/`; `README.md` agrega cómo desplegar en AWS. Sin cambios en `backend/` ni `frontend/`.
- Servicio Express: `PrimaryContainer.ContainerPort` 8000; `Environment` con `PORT=8000` y `AI_PROVIDER=mock`; `HealthCheckPath` `/api/health` (el valor por defecto es `/`); `Cpu` 512 y `Memory` 1024 (el valor por defecto es 1 vCPU y 2 GB); `ScalingTarget` con `MinTaskCount` 1 y `MaxTaskCount` 2; subredes públicas; `AwsLogsConfiguration` hacia un log group con retención corta. Con datos solo en memoria y sin escrituras, dos tareas no generan inconsistencias [I].
- Decisiones: la VPC propia se crea ya en esta fase, porque el primer servicio Express de una VPC fija si su ALB es público o interno y esa configuración no se puede editar después [V]. La imagen se publica con `DockerImageAsset` (CDK la construye y la sube a ECR en `cdk deploy`), lo que evita un `docker push` manual; la Fase 4 puede pasar a un repositorio ECR propio. Construir para linux/amd64, la arquitectura por defecto de Express [V].
- Variables nuevas: ninguna; `PORT` solo se fija explícito.
- Recursos AWS: VPC 2 AZ, ECR (activo de CDK), cluster ECS, rol de ejecución, rol de infraestructura, servicio Express (crea ALB HTTPS con certificado, SG, log group y alarmas de despliegue).
- Aceptación: `https://<endpoint>/api/health` responde `ok` con 500 niños y 2950 observaciones; `/` y `/nino/NINO-00002` cargan; `/api/no-existe` devuelve 404 JSON; los logs llegan a CloudWatch; la definición de tarea no tiene `AWS_ACCESS_KEY_ID`.

### Fase 1: IA real con task role, detrás de la abstracción actual · M

- Archivos nuevos en `backend/app/aws/` (nombres según los límites de carpetas del spec, design.md:1044): `bedrock.py` (portar `call_json` de integra-backend: Converse, tool use forzado, validación y backoff), `transcribe.py` (portar `ServicioTranscribe` de `servicio_transcripcion`) y `s3.py` (subir, leer y borrar con claves opacas).
- `services/ai.py`: rama `bedrock` con la misma firma (texto → `list[SugerenciaIA]`), en una sola llamada Converse con el roster de la sala y las 90 manifestaciones. El pipeline de varias llamadas de integra-backend queda para el trabajador de la Fase 2, porque en una petición síncrona puede acercarse al timeout de inactividad del ALB (60 s por defecto) [I].
- `main.py` y `models.py`: `CapturaRequest` recibe `id_jardin` y `sala_grupo`, y se elimina el atajo de main.py:128-130. Endpoints temporales: `POST /api/capturas/foto` (multipart a Converse con los bytes, sin guardar la foto) y `POST /api/transcripciones` + `GET /api/transcripciones/{id}` (audio a S3, `StartTranscriptionJob`, consulta con `GetTranscriptionJob` y respuesta con texto completo y confianza por palabra). Es una desviación temporal de la propuesta (solo el trabajador llama a la IA) que la Fase 2 elimina.
- `data.py`: `nombre_pila` determinista con lista fija y hash del ID (D6), para que Bedrock identifique por nombre.
- `config.py`, `.env.example` y `requirements.txt` (boto3 con versión exacta). Frontend: `CaptureBox` con foto (`capture="environment"` y reducción en el dispositivo, portando `reducirFoto` de huellita) y audio (MediaRecorder con selector de archivo alternativo, portando Captura.tsx de huellita); `SalaView` le pasa la sala.
- Variables nuevas: `AWS_REGION`, `FECHA_HOY`, `MODEL_ID_SUGERIR`, `BUCKET_CAPTURAS`, `TRANSCRIBE_IDIOMA`, `UMBRAL_PALABRA_DUDOSA`, `AUDIO_MAX_SEGUNDOS`, `MAX_BYTES_AUDIO`, `MAX_BYTES_FOTO`; `AI_PROVIDER` pasa a `bedrock`.
- Recursos AWS: bucket S3 privado (bloqueo de acceso público, SSE-S3, solo HTTPS, lifecycle de 1 día en `audio/` y `transcripciones/`, válido porque aún no hay revisión guardada en el servidor); task role con `bedrock:InvokeModel` sobre el perfil de inferencia y los modelos base de sus regiones, `transcribe:StartTranscriptionJob` y `GetTranscriptionJob`, y `s3:PutObject`, `GetObject` y `DeleteObject` sobre esos prefijos. Transcribe accede al bucket con los permisos de quien llama [PV].
- Aceptación: con `AI_PROVIDER=bedrock`, una nota con dos nombres devuelve sugerencias que registran el modelo; un audio de 60 s devuelve transcripción con palabras dudosas bajo 0,60; una foto de post-it devuelve texto y sugerencias; no hay claves en variables; los logs no contienen el texto de las notas.

### Fase 2: Aurora, siembra, idempotencia, cola y trabajador · L

- `DatosStack`: Aurora PostgreSQL Serverless v2 (motor 16.3 o superior), capacidad mínima 0, máxima 2, auto-pausa entre 300 y 600 s, credencial en Secrets Manager, subredes aisladas y SG con 5432 solo desde los SG de la API y del trabajador.
- `backend/app/datos/`: conexión con psycopg 3 y su pool (sin mínimo de conexiones y cerrando las ociosas); migraciones SQL numeradas con un runner propio, porque el proyecto evita dependencias (config.py:3-4) y Alembic con SQLAlchemy agrega peso; siembra idempotente de las 7 tablas y de `nino_app`; repositorio PostgreSQL con la misma interfaz que `DataStore`, para que `analytics.py` no cambie. Si no hay `DB_HOST`, se usa el `DataStore` CSV actual en modo lectura, así `ver-app.bat` y el desarrollo local siguen funcionando.
- `backend/app/capturas/`: los endpoints v0 del spec (design.md:1033 y siguientes): `POST /api/capturas` (202, `Idempotency-Key`, 422 para video, 413 y 415), detalle, corrección de transcripción y niños, confirmar, descartar y `GET /api/alertas/bandeja`. La API sube el objeto a S3 antes del 202 y deja captura y trabajo en una sola transacción; su task role queda en `s3:PutObject` (y `GetObject` para URLs breves de lectura). Se retiran los endpoints temporales de la Fase 1.
- `backend/app/trabajador/` (`python -m app.trabajador`, misma imagen): reclamo con `FOR UPDATE SKIP LOCKED`, arrendamiento y heartbeat; máximo 3 activos; reintentos con `proximo_intento_en`; pipelines de audio (Transcribe y luego Bedrock), foto y texto; escribe `sugerencia_ia`, nunca observaciones. La purga la encola la API al confirmar o descartar, en la misma transacción y con `proximo_intento_en = ahora + RETENCION_HORAS`, porque esas transiciones ocurren en la API y no en el trabajador. El lifecycle del bucket pasa a respaldo de 7 días.
- Migraciones: tarea ECS puntual (`RunTask` con la misma imagen y `python -m app.datos.migrar`) protegida con un advisory lock. No se ejecutan al arrancar la API porque el despliegue canary corre dos versiones a la vez.
- `AppStack`: servicio Fargate estándar del trabajador en el mismo cluster, 1 tarea, subredes públicas con IP pública y SG sin entrada, despliegue con mínimo 0 % y máximo 100 % para no tener dos trabajadores a la vez; `DB_USER` y `DB_PASSWORD` como secrets de ECS en la API y el trabajador.
- Frontend: `frontend/src/almacenamiento/` (IndexedDB con contenido crudo y clave, estado `esperando_conexion`, reenvío con la misma clave), bandeja cada 30 s y estados del ciclo de vida.
- `/api/health` sigue sin tocar la base. Pruebas nuevas en `backend/tests` con pytest contra un PostgreSQL local.
- Variables nuevas: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `WORKER_CONCURRENCIA`, `WORKER_ARRENDAMIENTO_S`, `WORKER_HEARTBEAT_S`, `TRANSCRIBE_POLL_S`, `UMBRAL_DEMORA_S`, `RETENCION_HORAS` y, si se porta el pipeline de integra-backend, sus `MODEL_ID_*`, `N_CORRIDAS_EVALUAR` y `TOP_K`.
- Aceptación: siembra con 20/80/500/9/90/2950/8850 e idempotente (P12); dos POST concurrentes con la misma clave dan un solo `id_captura` (P19); el 202 llega antes que Transcribe (P22); al matar la tarea del trabajador a mitad de un audio, el trabajo se retoma al vencer el arrendamiento y nunca hay más de 3 activos (P20); cero observaciones antes de confirmar (P8); la purga se ejecuta.

### Fase 3: SPA en S3 + CloudFront · M (opcional para la demo)

- `WebStack`: bucket privado con OAC; comportamiento por defecto hacia S3 con una CloudFront Function que reescribe a `/index.html` las rutas sin extensión; `/api/*` hacia el endpoint de Express sin caché, con todos los métodos y sin reenviar el `Host` del visitante, para que calce la regla por host del ALB [PV]. No usar respuestas de error personalizadas para el fallback: aplican a toda la distribución y convertirían los 404 y 403 de la API en `index.html` [I].
- Publicación de `frontend/dist` con `Cache-Control` inmutable para `assets/` y `no-cache` para `index.html` (las mismas reglas de main.py:156-160).
- `Dockerfile`: la imagen de ECS deja de incluir el SPA (un target sin la etapa de Node). FastAPI no registra el fallback si falta `index.html` (main.py:140), así que no cambia código. Sin variables nuevas.
- Aceptación: el SPA carga desde CloudFront con el bucket no público; los deep links funcionan; `/api/no-existe` devuelve 404 JSON; subir un audio de unos 5 MB por CloudFront funciona [PV].

### Fase 4: endurecimiento · M-L

- Cognito: user pool sin auto-registro, grupos educadora y directora, y jardín y salas como atributos. El login se hace en el backend (código OAuth y cookie HttpOnly) para respetar que la SPA solo habla con FastAPI (design.md:954); FastAPI aplica el alcance por jardín y sala en cada endpoint.
- Secretos: la credencial de Aurora ya llega en la Fase 2; aquí se agregan rotación y un secreto de origen que CloudFront envía como header y FastAPI exige, para que nadie use el ALB directo. ECS inyecta los secretos al iniciar la tarea, así que rotar exige redesplegar o usar usuarios alternos [I]. La guía de AWS para secretos recomienda clave KMS dedicada, rotación y políticas mínimas; para la demo basta la clave administrada.
- Observabilidad: métrica EMF con la edad del trabajo más antiguo, alarmas de esa métrica, de trabajador sin tareas, de 5xx del ALB y de throttling de Bedrock; SNS por correo; presupuesto de AWS Budgets.
- CI: `.github/workflows/ci.yml` (build, tests y `cdk synth`) y `deploy.yml` (OIDC con un rol limitado a `repo:BastiCan/Hackathon:ref:refs/heads/main` y `cdk deploy`); desactivar el autodeploy de Render. FastAPI sin `/docs` en AWS.
- Antes de usar datos reales de niños: revisar región y residencia de datos (README.md:114 cita la Ley 21.719; design.md:958).
- Variables nuevas: `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `COGNITO_DOMINIO`, `ORIGEN_SECRETO`, `DOCS_HABILITADAS`.
- Aceptación: sin sesión, 401; otra sala, 403; ALB directo, 403; un trabajo atascado dispara la alarma; un push a `main` despliega sin claves de larga duración.

## 4. Cambios por archivo

| Archivo | Fase | Cambio |
|---|---|---|
| `.dockerignore` | 0 | Excluir `.worktrees/`, `.agents/`, `infra/`, `**/cdk.out`, `servicio_transcripcion/` |
| `README.md` | 0, 4 | Despliegue en AWS; CI |
| `infra/` (nuevo) | 0-4 | App CDK (sección 6) |
| `backend/requirements.txt` | 1, 2, 4 | boto3; psycopg y psycopg-pool; librería OAuth/JWT; versiones exactas |
| `backend/.env.example` | 1, 2 | Variables nuevas, sin valores secretos |
| `backend/app/config.py` | 1, 2, 4 | Leer las variables nuevas; `FECHA_HOY` configurable |
| `backend/app/main.py` | 1, 2, 4 | Roster por sala; endpoints temporales y luego routers del spec; autenticación; `/docs` condicional |
| `backend/app/models.py` | 1, 2 | `id_jardin` y `sala_grupo` en `CapturaRequest`; contratos del spec |
| `backend/app/data.py` | 1, 2 | `nombre_pila`; modo CSV de respaldo |
| `backend/app/services/ai.py` | 1 | Rama `bedrock`; el mock queda para local y pruebas |
| `backend/app/services/analytics.py` | Ninguna | Sin cambios si el store mantiene su interfaz |
| `backend/app/aws/` (nuevo) | 1 | Adaptadores de S3, Transcribe y Bedrock |
| `backend/app/datos/` (nuevo) | 2 | Conexión, migraciones, siembra, repositorio |
| `backend/app/capturas/` (nuevo) | 2 | Captura, detalle, corrección, confirmación, bandeja |
| `backend/app/trabajador/` (nuevo) | 2 | Entrypoint, reclamo, pipelines, purga, métrica de cola |
| `backend/tests/` y `backend/requirements-dev.txt` (nuevos) | 2 | pytest |
| `frontend/src/api.ts` | 1, 2 | Foto y audio; `POST /api/capturas` con `Idempotency-Key`; detalle y bandeja |
| `frontend/src/components/CaptureBox.tsx` | 1, 2 | Foto y audio reales; guardar en IndexedDB antes de enviar |
| `frontend/src/views/SalaView.tsx` | 1, 2 | Pasar la sala a `CaptureBox` (:68); bandeja |
| `frontend/src/almacenamiento/` (nuevo) | 2 | IndexedDB y sincronización |
| `frontend/package.json` | 2, 4 | Script de test con vitest |
| `Dockerfile` | 3 | Target de API sin la etapa de Node; sin cambios en las fases 0-2 |
| `render.yaml` | 4 | Retirar o desactivar el autodeploy |
| `.github/workflows/` (nuevo) | 4 | CI y despliegue con OIDC |
| `ver-app.bat`, `frontend/vite.config.ts` | Ninguna | Sin cambios |

Si se elige huellita como frontend, las filas de `frontend/` pasan a `huellita-formato-mejorado/src/services/` (implementar `DataService` e `IAService` sobre HTTP) y la etapa 1 del `Dockerfile` compila esa carpeta.

## 5. Configuración y variables

| Variable | Fase | Tipo | Valor de demo | Nota |
|---|---|---|---|---|
| `DATASET_DIR`, `FRONTEND_DIST` | Actual | env | Por defecto | config.py:23-28 |
| `AI_PROVIDER` | Actual, 1 | env | `mock`, luego `bedrock` | config.py:29; render.yaml:16-17 |
| `PORT` | Actual | env | 8000 | Igual a `ContainerPort` |
| `FECHA_HOY` | 1 | env | 2026-10-13 | Hoy fija en main.py:36 |
| `AWS_REGION` | 1 | env | us-east-1 | |
| `MODEL_ID_SUGERIR` | 1 | env | ID del perfil de inferencia | Modelo multimodal por decidir |
| `BUCKET_CAPTURAS` | 1 | env | Salida de CDK | No reutilizar el nombre fijo de integra-backend (template.yaml:175) |
| `TRANSCRIBE_IDIOMA` | 1 | env | es-US | Benchmark es-US, es-MX, es-ES pendiente |
| `UMBRAL_PALABRA_DUDOSA` | 1 | env | 0.60 | |
| `AUDIO_MAX_SEGUNDOS` | 1 | env | 300 | Rechazar valores menores a 240 (D12) |
| `MAX_BYTES_AUDIO`, `MAX_BYTES_FOTO` | 1 | env | 10 MB y 3,5 MB | Converse acepta imágenes de hasta 3,75 MB (según postit-deteccion-ocr-investigacion.md §4) |
| `DB_HOST`, `DB_PORT`, `DB_NAME` | 2 | env | Salidas de CDK | |
| `DB_USER`, `DB_PASSWORD` | 2 | secret de ECS | Secrets Manager | Nunca en `Environment` ni en la plantilla |
| `WORKER_CONCURRENCIA` | 2 | env | 3 | D11 |
| `WORKER_ARRENDAMIENTO_S`, `WORKER_HEARTBEAT_S` | 2 | env | 120 y 30 [I] | |
| `TRANSCRIBE_POLL_S`, `UMBRAL_DEMORA_S`, `RETENCION_HORAS` | 2 | env | 5, por medir, 24 | Valores del spec |
| `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `COGNITO_DOMINIO` | 4 | env | Salidas de CDK | El secreto del cliente va como secret de ECS |
| `ORIGEN_SECRETO` | 4 | secret de ECS | Aleatorio | Header de CloudFront hacia el ALB |
| `DOCS_HABILITADAS` | 4 | env | false | |

En ECS no deben existir `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` ni `AWS_SESSION_TOKEN` (están como plantillas vacías en origin/main:integra-backend/.env.example:3-5, solo para uso local). boto3 toma el task role desde el endpoint de credenciales del contenedor sin configuración extra [I].

## 6. IaC propuesta (`infra/`, CDK en Python)

```
infra/
├─ app.py             instancia los stacks en us-east-1
├─ cdk.json
├─ requirements.txt   aws-cdk-lib y constructs con versión exacta
├─ stacks/            red, datos, app, web, observabilidad, cicd
└─ tests/             aserciones sobre las plantillas (pytest)
```

| Stack | Responsabilidad | Fase |
|---|---|---|
| `RedStack` | VPC 2 AZ con subredes públicas y aisladas, sin NAT; SG de API, trabajador y Aurora | 0 |
| `DatosStack` (con estado) | Bucket de capturas; Aurora y su secreto; políticas de borrado explícitas (demo: bucket con borrado de objetos, Aurora con snapshot) | 1-2 |
| `AppStack` (sin estado) | `DockerImageAsset`; cluster propio; roles de ejecución (con `GetSecretValue` solo sobre el secreto), infraestructura (política administrada de Express), task role de API y task role de trabajador; `CfnExpressGatewayService`; `FargateService` del trabajador; tarea de migración; log groups | 0-2 |
| `WebStack` | Bucket del SPA con OAC, CloudFront, CloudFront Function, publicación del build | 3 |
| `ObservabilidadStack` | SNS, alarmas, dashboard, presupuesto | 4 |
| `CicdStack` | Proveedor OIDC de GitHub y rol de despliegue | 4 |

- Datos y aplicación van en stacks separados para poder recrear la app sin tocar Aurora ni el bucket.
- El cluster propio se pasa en la propiedad `Cluster` del servicio Express; cambiarla después obliga a reemplazar el servicio [V].
- Para que Aurora acepte solo a la API, se entrega un SG propio en `NetworkConfiguration.SecurityGroups` y se referencia desde el SG de Aurora. No está claro si Express mantiene además su SG administrado para el tráfico del ALB [PV]; si no, el respaldo es permitir 5432 desde el CIDR de la VPC.
- Las pruebas de `infra/tests` comprueban: ningún bucket público, cero NAT, `ContainerPort` 8000 y ninguna acción IAM con comodín sin justificar.

Verificaciones en documentación AWS:

| Pregunta | Resultado |
|---|---|
| Parámetro de puerto en Express Mode | `PrimaryContainer.ContainerPort` en CloudFormation (`primaryContainer.containerPort` en la API), entero, por defecto 80 [V] |
| Health check | `HealthCheckPath`, por defecto `/`; intervalo 30 s, timeout 5 s, 5 chequeos para sano y 2 para no sano; gracia de 300 s [V] |
| ¿El trabajador puede compartir el cluster de Express? | Sí: los servicios Express pueden compartir cluster con servicios ECS no administrados por Express [V] |
| ¿`aws-cdk-lib` expone `CfnExpressGatewayService`? | Sí, `aws_cdk.aws_ecs.CfnExpressGatewayService` (L1), visto en la versión 2.273.0; no encontré un L2 y no confirmé la versión mínima [PV] |
| Otras restricciones de Express | La configuración del balanceador y la estrategia de despliegue no se editan; el primer servicio de la VPC fija ALB público o interno; `Cluster`, `ServiceName`, `InfrastructureRoleArn` y `Tags` requieren reemplazo; por defecto 1 vCPU, 2 GB y X86_64; hasta 25 servicios por ALB [V] |
| `ScalingTarget` | `MinTaskCount`, `MaxTaskCount`, `AutoScalingMetric` (AVERAGE_CPU, AVERAGE_MEMORY o REQUEST_COUNT_PER_TARGET) y `AutoScalingTargetValue` (60 por defecto) [V] |
| Auto-pausa de Aurora | PostgreSQL 16.3, 15.7, 14.12, 13.15 o superior; mínimo 0 ACU; espera de 300 a 86 400 s; reanuda en ~15 s (30 s o más tras 24 h en pausa); cualquier conexión de usuario abierta, aunque esté ociosa, o un RDS Proxy impiden la pausa [V] |
| Formatos de Transcribe por lotes | AMR, FLAC, M4A, MP3, MP4, Ogg, WebM y WAV, que cubren lo que graba MediaRecorder [V] |
| Bedrock Converse | Se autoriza con `bedrock:InvokeModel`; las imágenes desde S3 solo funcionan con algunos modelos, así que conviene enviar los bytes [V] |
| App Runner | Sin clientes nuevos desde el 30-04-2026 [V] |
| Aurora DSQL | Usa concurrencia optimista y `FOR UPDATE` no bloquea [V]; lo de `SKIP LOCKED` y `SAVEPOINT` no lo reverifiqué [PV] |
| Puerto 80 sin root en Fargate, si Express define `PORT`, si el health check sigue a `ContainerPort` | [PV]; se evita usando 8000 en el contenedor y en `PORT` |

## 7. Riesgos y decisiones pendientes

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Cuenta del evento con IAM restringido | Express, `cdk bootstrap` o los roles vinculados fallan | H0 antes de escribir IaC [PV] |
| El trabajador mantiene Aurora despierta; la reanudación tarda más que el timeout del health check | Costo continuo mientras corre el trabajador; tareas marcadas no sanas si `/api/health` toca la base | `/api/health` sin base; timeouts de conexión de más de 15 s con reintento; trabajador a 0 tareas fuera de la demo; pool sin conexiones ociosas |
| El lifecycle de S3 cuenta desde la creación del objeto, no desde el estado terminal [I] | Un respaldo corto podría borrar audio aún en revisión | Purga principal como trabajo encolado; respaldo de 7 días desde la Fase 2 |
| API pública sin autenticación y con `/docs` | Cualquiera puede leer y llamar la API | Solo datos sintéticos (README.md:52) hasta la Fase 4 |
| Fotos de celular de más de 3,75 MB | Converse las rechaza | Reducir en el dispositivo (fotos.ts:27) o en el servidor |
| Starlette guarda en un archivo temporal los multipart de más de 1 MB [I] | Choca con una lectura estricta de "sin disco local" (D9) | Si el equipo lo exige, cuerpo binario con tope de tamaño; la durabilidad igual depende de S3 |
| Dos trabajadores durante un despliegue | Más de 3 trabajos activos | Despliegue con mínimo 0 % y máximo 100 %, y límite también en SQL |
| Nombres de trabajos de Transcribe únicos por cuenta y región [I] | Choque con `servicio_transcripcion` o integra-backend en la misma cuenta | Prefijo propio por entorno |
| Contexto de build con `.worktrees/` | Builds lentos | `.dockerignore` en la Fase 0 |
| Costos fijos (ALB, IPv4 públicas, almacenamiento de Aurora) [I] | Cobro aunque no haya tráfico | Borrar los stacks después del hackathon |
| Plazo del hackathon | Fases 2 a 4 no alcanzan | Fase 0 + Fase 1 primero |

Decisiones que debe tomar el equipo:

1. Frontend a desplegar: `frontend/` (conectado a FastAPI y al dataset E-1 de 9 niveles) o `huellita-formato-mejorado/` (PWA y captura listas, sin backend y con rúbrica 8 × 8). Si es huellita, cambian la etapa 1 del `Dockerfile` y el `WebStack`, hay que implementar `DataService` e `IAService` sobre HTTP y conciliar la rúbrica. Conviene decidirlo antes de la Fase 1, porque define dónde se hace el trabajo de captura.
2. Línea de backend: FastAPI (`backend/`) con trabajador, reutilizando `core/` de integra-backend y `ServicioTranscribe`, o seguir con SAM, Lambda y DynamoDB. El spec y la propuesta piden lo primero (design.md:56); integra-backend tiene D1, D2 y D5 por discutir. Elegir FastAPI implica congelar `template.yaml`.
3. Ramas: `lucas/kiro-specs` está 25 commits detrás de `origin/main` y `design.md` no está en `origin/main`; conviene integrarlas antes de implementar.
4. `servicio_transcripcion/`: confirmar quién lo está escribiendo y si se versiona aparte o se absorbe en `backend/app/aws/`.
5. Modelo de Bedrock multimodal (Haiku 4.5 o Sonnet 5 de integra-backend, o Haiku 5.5 del informe de post-its) y su acceso en la cuenta.
6. Render: mantenerlo como respaldo durante el hackathon o retirarlo al terminar la Fase 0.
7. Aurora en la demo: aceptar el costo de tenerla activa con el trabajador o apagar el trabajador entre sesiones.
8. Región y residencia de datos antes de cualquier dato real.

## Fuentes

- [AWS::ECS::ExpressGatewayService](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ecs-expressgatewayservice.html), [ExpressGatewayContainer](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-ecs-expressgatewayservice-expressgatewaycontainer.html) y [ExpressGatewayScalingTarget](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-ecs-expressgatewayservice-expressgatewayscalingtarget.html)
- [Resources created by Amazon ECS Express Mode services](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/express-service-work.html)
- [aws-cdk-lib.aws_ecs.CfnExpressGatewayService (Python)](https://constructs.dev/packages/aws-cdk-lib/v/2.273.0/api/CfnExpressGatewayService?lang=python&submodule=aws_ecs)
- [Aurora serverless: scaling to zero ACUs with automatic pause and resume](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2-auto-pause.html)
- [Amazon Transcribe: data input and output](https://docs.aws.amazon.com/transcribe/latest/dg/how-input.html)
- [Bedrock: inference using Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html) y [ImageSource S3Location](https://docs.aws.amazon.com/sdk-for-kotlin/api/latest/bedrockruntime/aws.sdk.kotlin.services.bedrockruntime.model/-image-source/-s3-location/index.html)
- [AWS Service Availability Updates (marzo de 2026)](https://aws.amazon.com/about-aws/whats-new/2026/03/aws-service-availability/)
- [DSQL SQL dialect](https://aws.amazon.com/blogs/database/dsql-sql-dialect-how-amazon-aurora-dsql-differs-from-single-instance-postgresql/)

El contenido de la documentación de AWS se parafraseó por cumplimiento de licencias.
