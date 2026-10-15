# Guía paso a paso con Kiro

Objetivo de esta etapa: **una Lambda en AWS que recibe una nota y la procesa con LLM** (separar general/particular,
identificar al niño/a o dar error, evaluable y nivel con RAG), con datos en DynamoDB y S3. Nada más.

Copia y pega los prompts. Entre `[ ]` va lo que reemplazas.

---

## FASE 0 — Antes de abrir Kiro (tú)
1. Instala AWS CLI v2, AWS SAM CLI, Python 3.13 y Node.js LTS (`docs/AWS_SETUP.md` §0).
2. Credenciales del evento como variables de entorno **en la terminal de Kiro** y verifica con `aws sts get-caller-identity` (`docs/AWS_SETUP.md` §1).
3. En Bedrock (us-east-1) confirma Claude Haiku 4.5, Claude Sonnet 5 y Titan Embeddings V2, y anota sus IDs (§2).
4. Revisen en equipo `docs/DECISIONES.md`.
5. **Git** (en PowerShell, dentro de `breaking barrier\Hackathon`):
   ```powershell
   git config core.autocrlf true          # evita que Windows marque archivos como modificados solo por fines de línea
   git pull                                # traer lo último del equipo
   git checkout -b feature/integra-backend # rama propia para este trabajo
   git add integra-backend                 # SOLO esta carpeta (no "git add ." : hay archivos ajenos marcados)
   git commit -m "integra-backend: steering, spec, prompts y datos de evaluación"
   git push -u origin feature/integra-backend
   ```
   Después, para compartir: Pull Request a `main` en GitHub (o `git checkout main; git merge feature/integra-backend; git push`
   si el equipo prefiere trabajar directo en main).

## FASE 1 — Abrir Kiro
1. File → **Open Folder** → `breaking barrier\Hackathon\integra-backend` (la subcarpeta, no la raíz del repo: ahí está `.kiro/`).
   Git funciona igual: Kiro detecta el repo de la carpeta de arriba.
2. Modelo del chat de Kiro: el que prefieras (p. ej. Claude Opus 5.5). Es independiente de los modelos que usa el backend en Bedrock.
3. Verifica en el panel de Kiro: *Agent Steering* con `product`, `tech`, `structure`, `dominio`; *MCP Servers* con `aws-docs`.
4. Pega:

> **PROMPT 1 — Orientación**
> Lee el steering (#product #tech #structure #dominio), el spec
> #[[file:.kiro/specs/backend-observaciones/requirements.md]] #[[file:.kiro/specs/backend-observaciones/design.md]]
> #[[file:.kiro/specs/backend-observaciones/tasks.md]], #[[file:docs/DECISIONES.md]], los prompts #[[folder:src/prompts]]
> y los datos de prueba #[[folder:tests/fixtures]]. No escribas código todavía. Respóndeme:
> 1. Resumen de 10 líneas de lo que vas a construir y qué recursos de AWS vas a crear.
> 2. Contradicciones o huecos entre los documentos.
> 3. Qué necesitas de mí antes de la tarea 1.
> Contexto del repo: esta carpeta es `integra-backend/` dentro del repo `BastiCan/Hackathon`. Trabaja SOLO dentro de
> `integra-backend/`. Las carpetas de arriba (`backend/` con FastAPI, `frontend/`, `Dump/`, `Dockerfile`, `render.yaml`) son
> ideas de otros integrantes: no las leas como referencia, no reutilices su código y no las modifiques. Los archivos que
> están en el repo y no aparecen en #structure no son parte de este proyecto.
> La entrada del clasificador es SIEMPRE el texto escrito por las tías (`nota`), nunca el texto de la rúbrica.
> Archivos que ya existen y NO debes regenerar ni reescribir: `data/processed/rubrica.json`, `data/processed/fewshot.json`,
> `tests/fixtures/*.json`, `src/prompts/*.md`, `src/schemas/*.json`.
> Git: haz un commit por tarea terminada (`git add integra-backend` y mensaje "tarea N: …"), solo en la rama
> `feature/integra-backend`; nunca `git add .`, nunca push forzado, y no hagas push sin preguntarme.
> Reglas para toda la sesión: alcance mínimo, NO agregues API Gateway, endpoints, frontend, Step Functions ni ningún
> servicio fuera de #tech; una tarea a la vez; no cambies los prompts de `src/prompts/` ni las decisiones sin mostrarme el
> diff y explicarme por qué; nunca ejecutes `sam deploy` ni comandos que creen o borren recursos en AWS sin mi
> confirmación; las credenciales son variables de entorno temporales de la terminal (no uses `--profile`; si ves `ExpiredToken`, avísame).

## FASE 2 — Tareas 1 a 3 (sin AWS)
Botón **Start task** en `tasks.md`, o:

> **PROMPT 2 — Tarea**
> Ejecuta la tarea [N] de #[[file:.kiro/specs/backend-observaciones/tasks.md]]. Al terminar corre los tests que
> correspondan, muéstrame el resultado, marca la tarea como completada y detente.

Al terminar la 3: `py -3.13 -m pytest tests/unit -q`. El test de edad debe reproducir la tabla de `dominio.md` §1.

## FASE 3 — Tareas 4 a 7 (Bedrock desde tu computador)
En la terminal de Kiro, las variables de `docs/AWS_SETUP.md` §3. Para la tarea 4 agrega al PROMPT 2:
> Antes de escribir `llm.py`, consulta con el MCP aws-docs cómo usar structured outputs con la Converse API de Bedrock
> para Claude; si no aplica a nuestros modelos, usa tool use forzado como dice #tech.

Tareas 4, 5, 6 y 7 con el PROMPT 2. Luego:

> **PROMPT 3 — Checkpoint (tarea 7b)**
> 1. Corre `scripts/medir.py` sobre `tests/fixtures/validacion_100.json` usando solo el campo `nota` y muéstrame el reporte:
>    accuracy de código, recall/precisión de códigos, nivel exacto y ±1, dominio, y accuracy por certeza.
> 2. Corre `scripts/pipeline_local.py --casos tests/fixtures/notas_prueba.json` (nómina `tests/fixtures/nomina_demo.json`,
>    educadora EDU-0001, sala SG-A, fecha 2026-10-15) y muéstrame una tabla: nota | esperado | obtenido | ¿coincide? |
>    hipótesis si falla (prompt, validación, retriever o caso ambiguo).
> No cambies nada todavía.

Revísenlo en equipo. Si el accuracy de código sale absurdamente bajo, pide `medir.py --depurar` (usa el texto literal de la
rúbrica: si ahí también falla, el error es del código, no del modelo). Si algo falla, se corrige el prompt mirando los errores de la tabla de 13 casos, **nunca** los de
`validacion_100.json` (ese set solo mide):
> Propón un cambio mínimo en `src/prompts/[archivo].md` para corregir [caso]. Muéstrame el diff y vuelve a correr todo.

## FASE 4 — Tareas 8 y 9 (AWS)
Tarea 8 con el PROMPT 2. Luego:

> **PROMPT 4 — Antes de desplegar**
> Revisa `template.yaml` contra #tech y el diseño: lista los recursos que se crearán (deben ser 1 Lambda, 3 tablas,
> 1 bucket y 1 rol) y los permisos del rol. Dame, sin ejecutarlos, los comandos de `sam build` y
> `sam deploy --guided` con el valor de cada parámetro.

Tú ejecutas el deploy (`docs/AWS_SETUP.md` §4). Después:

> **PROMPT 5 — Datos y prueba**
> El stack está desplegado; los outputs son [pega los Outputs]. Ejecuta `scripts/cargar_aws.py` y
> muéstrame los conteos. Luego invoca la función con `sam remote invoke` y `events/nota_ejemplo.json`, muéstrame la
> respuesta y los registros que quedaron en la tabla `Observaciones`.

Listo: la etapa está cumplida cuando esa invocación devuelve las observaciones separadas, con niño/a o error, y nivel sugerido, y quedan guardadas en DynamoDB.

## Si Kiro se desvía
- "Detente. Eso está fuera del alcance de #product. Vuelve atrás."
- "Eso contradice #dominio [sección]. Explícame qué ibas a resolver."
- "No inventes IDs de modelo: léelos de las variables de entorno."
