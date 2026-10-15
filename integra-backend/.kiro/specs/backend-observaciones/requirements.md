# Requirements Document — Procesador de notas de sala

## Introduction
Una función Lambda en AWS que recibe una nota en texto libre con la educadora, la sala y la fecha; separa con un LLM los
fragmentos generales y particulares y los guarda como textos propios; identifica al niño/a de cada fragmento particular
(o devuelve error si no puede); y, para los particulares identificados, decide si son evaluables y sugiere el nivel con RAG
sobre la rúbrica. Alcance mínimo: ver `product.md` (sin API, sin frontend, sin Step Functions).

## Requirements

### Requirement 1: Entrada
**User Story:** Como equipo, queremos invocar una función con una nota y su contexto, para obtener las observaciones procesadas.

#### Acceptance Criteria
1. WHEN la Lambda recibe `{"texto", "id_educadora", "sala_grupo", "fecha"}` THE SYSTEM SHALL procesar la nota y devolver `{"id_captura", "observaciones": [...]}`.
2. IF `texto` está vacío THEN THE SYSTEM SHALL devolver `{"error": {"codigo": "TEXTO_VACIO"}}` sin llamar al LLM.
3. IF la educadora no existe THEN `EDUCADORA_DESCONOCIDA`; IF la sala no tiene niños/as en el jardín de la educadora THEN `SALA_DESCONOCIDA`.

### Requirement 2: Nómina y edad
#### Acceptance Criteria
1. THE SYSTEM SHALL deducir el jardín desde la educadora y cargar los niños/as de ese jardín desde DynamoDB, separando los de la sala pedida (nómina) del resto (para detectar FUERA_DE_SALA).
2. THE SYSTEM SHALL considerar solo niños/as con `fecha_ingreso <= fecha`.
3. THE SYSTEM SHALL NOT enviar edad, nivel esperado ni historial a ninguna llamada al LLM; la edad solo se usa en código después de evaluar (`dominio.md` §1).

### Requirement 3: Separación general / particular
**User Story:** Como tía, quiero que mi nota se divida sola en lo general y lo de cada niño/a.

#### Acceptance Criteria
1. THE SYSTEM SHALL dividir la nota con el LLM en fragmentos `GENERAL` o `PARTICULAR`, cada uno con `texto_literal` copiado del original.
2. THE SYSTEM SHALL verificar que cada `texto_literal` exista en el original (comparación normalizada) y registrar `TEXTO_NO_CUBIERTO` si queda texto sustantivo sin asignar.
3. THE SYSTEM SHALL guardar cada fragmento como su propio registro en la tabla `Observaciones` (los `GENERAL` sin evaluación).

### Requirement 4: Identificación del niño/a
**User Story:** Como tía, quiero que cada observación quede con el niño/a correcto o que se me avise que no se pudo.

#### Acceptance Criteria
1. THE SYSTEM SHALL distinguir sujetos de niños/as solo mencionados y de adultos; solo los sujetos generan observaciones.
2. WHEN un fragmento tiene N sujetos THE SYSTEM SHALL crear N observaciones con el mismo texto.
3. THE SYSTEM SHALL aceptar solo referencias que existan en la nómina; una referencia inventada se trata como no resuelta.
4. IF el nombre no calza con nadie de la sala THEN `tipo = NO_IDENTIFICADO`, `error = NO_ENCONTRADO`, salvo que calce con un niño/a de otra sala del jardín → `FUERA_DE_SALA`.
5. IF el nombre calza con dos o más niños/as THEN `NO_IDENTIFICADO` con `error = AMBIGUO`.
6. THE SYSTEM SHALL adjuntar hasta 3 `candidatos` (id, nombre, puntaje) a todo `NO_IDENTIFICADO`, guardarlo igual y seguir con los demás fragmentos.

### Requirement 5: Logs
#### Acceptance Criteria
1. THE SYSTEM SHALL NOT escribir el texto de las notas en CloudWatch Logs (solo IDs, conteos y tiempos).

### Requirement 6: Evaluabilidad
**User Story:** Como equipo, queremos decidir solo con el texto si una observación sirve para evaluar.

#### Acceptance Criteria
1. WHEN una observación es `PARTICULAR` identificada THE SYSTEM SHALL extraer conductas atómicas (`accion`, `frase_literal`, `iniciativa`, `apoyo`, `complejidad`, `tipo_contenido`).
2. IF ninguna conducta es `tipo_contenido = conducta` THEN `evaluabilidad = NO_EVALUABLE` con `motivo`; la observación se guarda igual.
3. THE SYSTEM SHALL aplicar el criterio de `dominio.md` §4 y, ante la duda, preferir `EVALUABLE`.

### Requirement 7: RAG sobre la rúbrica
#### Acceptance Criteria
1. THE SYSTEM SHALL cargar `rubrica.json`, `fewshot.json` y los embeddings desde S3 (`rubrica/`) al iniciar la Lambda.
2. WHEN se evalúa una observación THE SYSTEM SHALL recuperar, por cada conducta, las `TOP_K` manifestaciones más similares a su `accion` entre las 90, sin filtro de nivel.
3. THE SYSTEM SHALL entregar al LLM las descripciones de los 9 niveles de `ruta_niveles` junto con las manifestaciones candidatas.

### Requirement 8: Código de manifestación y nivel
**User Story:** Como tía, quiero la manifestación evidenciada (y por ende el nivel) con su evidencia y certeza.

#### Acceptance Criteria
1. THE SYSTEM SHALL pedir al LLM solo el o los `id_manifestacion` (máx. 3) con su `frase_evidencia`, un `otro_codigo_viable` y un `comentario`, usando los 9 ejemplos de `data/processed/fewshot.json` en el prompt.
2. THE SYSTEM SHALL restringir los códigos con el esquema de salida a los 90 de `rubrica.json`, y verificar que `frase_evidencia` sea literal.
3. THE SYSTEM SHALL obtener `nivel`, `dominio` y `texto_observable` de cada código por cruce con `rubrica.json`, sin IA.
4. THE SYSTEM SHALL correr la clasificación `N_CORRIDAS_EVALUAR` veces y consolidar códigos, certeza y comentario por votación (`dominio.md` §5).
5. IF la observación es NO_EVALUABLE o no tiene correspondencia THEN `nivel = null` (nunca 0).
6. THE SYSTEM SHALL agregar en código `edad_meses`, `niveles_esperados` y `comparacion_edad` (`BAJO_LO_ESPERADO` | `ACORDE` | `SOBRE_LO_ESPERADO`) según `ruta_niveles`, y una frase con esa información al final del `comentario`.
7. THE SYSTEM SHALL guardar el resultado en `Observaciones` con `estado = SUGERIDO`, `prompt_version` y `model_id`.

### Requirement 9: Datos en AWS
#### Acceptance Criteria
1. THE SYSTEM SHALL incluir un script que cargue en DynamoDB las educadoras y los niños/as (con los nombres de demo de `tests/fixtures/nomina_demo.json` donde existan) y suba a S3 `rubrica.json`, `fewshot.json`, los embeddings y el dataset original (`raw/`).
2. THE SYSTEM SHALL permitir correr el mismo pipeline en local con `FUENTE_DATOS=local` (sin DynamoDB/S3, con Bedrock real).

### Requirement 10: Medición de accuracy
**User Story:** Como equipo, queremos saber qué tan bien el sistema encuentra el código de manifestación.

#### Acceptance Criteria
1. THE SYSTEM SHALL incluir `scripts/medir.py` que corra la clasificación sobre `tests/fixtures/validacion_100.json` (protagonista conocido: mide solo conductas + clasificación) usando SOLO el campo `nota` (texto escrito como lo anota una tía). `texto_control` (texto literal de la rúbrica) existe únicamente para depurar errores de código y NUNCA se reporta como resultado.
2. THE SYSTEM SHALL reportar: accuracy de código (conjunto exacto), recall y precisión de códigos, accuracy de nivel (exacto y ±1), accuracy de dominio, y accuracy por nivel de certeza (alta/media/baja).
3. THE SYSTEM SHALL NOT usar `validacion_100.json` para ajustar prompts ni elegir ejemplos.
