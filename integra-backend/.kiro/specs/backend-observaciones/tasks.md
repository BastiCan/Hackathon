# Implementation Plan

> Una tarea a la vez, revisando el diff. ⏸ = punto de control con el equipo. No agregar nada fuera de `product.md`.

- [ ] 1. Esqueleto
  - `pyproject.toml` (Python 3.13; boto3, pydantic>=2, jsonschema, rapidfuzz, python-ulid; dev: pytest, ruff), `.gitignore` (`.env`, `.aws-sam/`, `__pycache__/`), carpetas de `structure.md`
  - `src/core/config.py` (env vars; `FUENTE_DATOS=local|aws`) y `src/core/modelos.py` (enums de `dominio.md` §2)
  - _Requirements: 9.2_

- [ ] 2. Datos procesados (YA GENERADOS: `data/processed/rubrica.json`, `data/processed/fewshot.json`; NO regenerarlos)
  - `src/core/rubrica.py`: carga `rubrica.json` y cruza código → nivel, dominio, texto_observable
  - NO generar nombres: usar `tests/fixtures/nomina_demo.json` (ya escrito; nombres de demo sobre niños/as reales de JAR-0001)
  - Test: `rubrica.json` tiene 9 niveles, 5 dominios y 90 códigos; `fewshot.json` tiene 9 ejemplos (1 por nivel) y **cada `respuesta` valida contra `src/schemas/clasificar.json`** (con los enums ya resueltos, igual que en `llm.py`)
  - _Requirements: 4.4, 4.5, 9.1_

- [ ] 3. Dominio puro con tests unitarios
  - 3.1 `edad.py` (el test debe reproducir exactamente la tabla de `dominio.md` §1)
  - 3.2 `nombres.py` · 3.3 `validaciones.py` · 3.4 `postproceso.py`
  - _Requirements: 3.2, 4.3–4.6, 8.2–8.5_

- [ ] 4. `llm.py` (Converse; structured outputs o tool use forzado; validación; reintentos; `LlmMeta`; reemplazo de `x-enum-from`/`x-range-from`)
  - Test `-m llm` mínimo con una llamada real
  - _Requirements: 8.6_

- [ ] 5. Embeddings y retriever
  - `scripts/embeber_rubrica.py` → `data/processed/embeddings_rubrica.json`
  - `retriever.py` (coseno en Python puro sobre las 90 manifestaciones, sin filtro de nivel)
  - _Requirements: 7.1, 7.2_

- [ ] 6. Pipeline
  - 6.1 `datos.py` (implementación local primero) y `pipeline.py` usando los prompts (`separar_identificar`, `extraer_conductas`, `clasificar`) y esquemas existentes (no reescribirlos); el prompt `clasificar` recibe los ejemplos de `fewshot.json`
  - 6.2 `scripts/pipeline_local.py`
  - 6.3 `datos.py` local lee `tests/fixtures/nomina_demo.json` (ya escrito; no modificarlo)
  - 6.4 `tests/llm/test_notas_prueba.py` con los 13 casos de `tests/fixtures/notas_prueba.json` (ya escrito; no modificarlo); `pipeline_local.py --casos` imprime la tabla esperado vs obtenido
  - _Requirements: 1.1–1.3, 2.1–2.3, 3.1, 3.3, 4.1, 4.2, 6.1–6.3, 7.2, 7.3, 8.1, 8.6_

- [ ] 7. Medición (`scripts/medir.py`)
  - Corre conductas + clasificación sobre `tests/fixtures/validacion_100.json` usando SOLO el campo `nota` (lo escrito por la tía). `texto_control` solo con el flag `--depurar`, nunca en el reporte
  - Reporta las métricas del Requirement 10 en `data/eval/reporte.md` y el detalle por caso en `data/eval/resultados.jsonl`
  - _Requirements: 10.1–10.3_

- [ ] 7b. ⏸ Checkpoint de calidad: correr `medir.py` y correr `pipeline_local.py` con los 13 casos de `tests/fixtures/notas_prueba.json` y revisar en equipo antes de tocar AWS

- [ ] 8. AWS
  - 8.1 `datos.py` implementación DynamoDB; `config.py` lee `rubrica/` desde S3 al iniciar
  - 8.2 `src/handler.py` y `events/nota_ejemplo.json`
  - 8.3 `template.yaml`: 1 Lambda (Python 3.13, 300 s, 1024 MB), 3 tablas on-demand, 1 bucket (acceso público bloqueado, cifrado), rol IAM mínimo (`bedrock:InvokeModel` sobre inference profiles y modelos fundacionales usados; `dynamodb:GetItem/Query` en Educadoras y Ninos; `dynamodb:PutItem/BatchWriteItem` en Observaciones; `s3:GetObject` en `rubrica/*`). Parámetros: `ModelIdSeparar`, `ModelIdConductas`, `ModelIdEvaluar`, `ModelIdEmbeddings`, `NCorridas`. Outputs: nombre de la función, del bucket y de las tablas
  - 8.4 `scripts/cargar_aws.py`: carga Educadoras (80) y Ninos (500; con `nombre`/`apodos` de `nomina_demo.json` cuando existan); sube a `rubrica/` los archivos `rubrica.json`, `fewshot.json` y `embeddings_rubrica.json`, y `data/raw/` a `raw/`; imprime conteos
  - _Requirements: 7.1, 9.1_

- [x] 8b. Entrada por S3 — dominio puro primero
  - `src/core/capturas.py`: `id_captura_de_clave` (valida `CAP-<ULID>`), `tipo_de_clave` (`meta`|`texto`|`otro`), `clave_archivo` + tests unitarios
  - `modelos.py`: `Meta`, `TextoCaptura`/`Parte`, enums de estado de `Registros`; `id_obs = {id_captura}-p{n_parte}-{n_obs}`
  - `pipeline.procesar_nota` recibe `id_captura`, `n_parte` y `archivo_s3` (no genera el id); una parte = una nota; `archivo_s3` se copia a sus observaciones
  - _Idempotencia e IDs deterministas_

- [x] 8c. Datos AWS — nuevas tablas y escrituras
  - `datos_aws.py`: `Jardines`; `Educadoras`/`Ninos` con GSI `porJardin`; `Registros` (upsert de `meta` y de estado, GSI `porSala` SK subido_en);
    `Observaciones` con `sala_key`, `origen`, `orden`, `archivo_s3` y GSI `porNino`/`porSala`; `UpdateItem` en `Ninos` (ultima_obs_fecha, ultimo_nivel, ultimo_nivel_fecha)
  - Fechas ISO 8601 con zona `-03:00`; `sala_key = "{id_jardin}#{sala_grupo}"`; `orden = "{fecha}#{creado_en}"`
  - Tests unitarios de serialización/claves (sin AWS)

- [x] 8d. Handler disparado por S3
  - `handler.py`: records S3 → `meta.json` upsert `Registros` RECIBIDO; `texto.json` → PROCESANDO, procesa cada parte, PROCESADO/SIN_TEXTO/ERROR con `errores[]` por parte
  - La invocación directa (evento JSON) sigue funcionando para pruebas; `id_captura` opcional
  - `events/s3_meta.json` y `events/s3_texto.json` de ejemplo

- [x] 8e. `template.yaml` — 2º bucket y disparadores
  - Bucket `capturas` con nombre fijo (`!Sub` + `${AWS::AccountId}`); 2 notificaciones S3 a `ProcesarNota` (prefijo `capturas/`, sufijos `meta.json` y `texto.json`)
  - Tablas `Jardines` y `Registros` + GSIs (`porJardin`, `porSala`, `porNino`); permisos nuevos: `s3:GetObject` en `capturas/*`, `dynamodb:PutItem/UpdateItem` en `Registros`, `dynamodb:UpdateItem` en `Ninos`
  - Parámetros/outputs nuevos (nombre del bucket de capturas y de las tablas nuevas)

- [ ] 8f. Carga ampliada y captura de prueba
  - `cargar_aws.py`: cargar `Jardines` (CSV + `salas[]` deducidas de `ninos.csv`), `Educadoras`, `Ninos`; e historial de `consolidado.json` en `Observaciones` (`origen=dataset`), calculando `ultima_obs_fecha`/`ultimo_nivel`/`ultimo_nivel_fecha` por niño. Dejar de subir `raw/`
  - `scripts/subir_captura_prueba.py`: genera `CAP-<ULID>` y sube `meta.json` + `texto.json` de una nota de prueba (dispara el flujo sin OCR)

- [ ] 9. ⏸ Despliegue y prueba (yo ejecuto `sam deploy`; ver `docs/AWS_SETUP.md`)
  - `sam remote invoke` con `events/nota_ejemplo.json` (invocación directa)
  - `scripts/subir_captura_prueba.py` para probar el disparo S3; verificar `Registros` (RECIBIDO→PROCESADO) y `Observaciones`
