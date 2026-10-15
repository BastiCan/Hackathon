# Capturas asíncronas con corrección auditable y reprocesamiento AWS

El documento integra las decisiones cerradas sobre nombres de pila, espera de conectividad, audio largo y procesamiento asíncrono detrás de FastAPI. La idempotencia de confirmación señalada en la revisión anterior ya fue corregida: ahora se autoriza y se atiende el estado `confirmada` antes de exigir un estado revisable. Sin embargo, la corrección de una transcripción encola un nuevo procesamiento Bedrock sin cambiar el estado de la captura ni impedir una confirmación concurrente. Esa contradicción deja el progreso reportado y las sugerencias revisables fuera de sincronía.

**Watch for:** **confirmado** — `corregirTranscripcion` invalida sugerencias y encola Bedrock, pero la captura permanece en `lista_para_revisar` o `revision_manual`; ambos estados siguen habilitando `confirmarCaptura` mientras el reprocesamiento está pendiente.

**Verdict**: NEEDS_CHANGES

## High-level view

La experiencia principal es asíncrona y tolera pérdida de conectividad sin ejecutar IA local. IndexedDB conserva el contenido y la clave hasta recibir 202; FastAPI deja captura, objeto y trabajo durables, y PostgreSQL permite recuperar trabajos con concurrencia inicial de tres.

FastAPI mantiene la frontera exclusiva con S3, Amazon Transcribe y Amazon Bedrock. El audio se captura en formatos de navegador durante al menos cuatro minutos, se transcribe por lotes y conserva texto completo, confianza por palabra e información del proveedor antes de generar propuestas sujetas a confirmación humana.

**Confirmado:** el subflujo de corrección crea trabajo nuevo sin una transición desde el estado revisable hacia `en_cola` o `procesando`. La bandeja puede anunciar resultados revisables que ya fueron invalidados y la API puede confirmarlos antes de que termine el reprocesamiento.

<details>
<summary>Issues (1)</summary>

1. **Ciclo de corrección sin estado — confirmado** — `corregirTranscripcion` encola Bedrock sin sacar la captura de un estado confirmable. Restringir los estados de entrada, persistir atómicamente una transición a cola/procesamiento y alinear diagrama, contrato, endpoint y prueba de concurrencia.

</details>

<details><summary>Details</summary>

## Verificación criterio por criterio

### 1. Documento completo, coherente y en español

Cumple salvo la contradicción bloqueante del reprocesamiento descrita en los criterios 10, 12 y 13. Todas las secciones están desarrolladas en español; los términos restantes en inglés son nombres técnicos o identificadores.

### 2. Nombres de pila sin alias vigente

Cumple. `nombre_pila` se usa desde el glosario y D5-D6 hasta modelos, algoritmos, contratos, pruebas y reparto de trabajo. No queda un alias de fauna ni un campo de alias vigente.

### 3. Retiro de `local_lexico`

Cumple. Los proveedores definidos son Amazon Transcribe y Amazon Bedrock; no queda proveedor local, fallback léxico ni meta equivalente.

### 4. Video solo como compatibilidad histórica

Cumple. D7, las reglas heredadas, P17, las pruebas y los endpoints limitan las capturas nuevas a `foto|audio|texto`, representan `video` histórico como solo lectura y devuelven 422 al intentar crearlo.

### 5. Espera de conectividad sin IA local

Cumple. `esperando_conexion` existe solo en IndexedDB; el contenido y `Idempotency-Key` sobreviven recargas, esperan red y se retiran tras 202. Los reenvíos reutilizan la clave para una aceptación lógica única; las ejecuciones externas son reintentables e idempotentes.

### 6. FastAPI como única frontera AWS

Cumple. Arquitectura, D9-D10, P21, seguridad y dependencias ubican credenciales y llamadas S3/Transcribe/Bedrock en backend. La SPA no recibe credenciales ni URLs de escritura; Lambda, SAM y API Gateway no son requisitos y el alojamiento no queda ligado a Render.

### 7. Aceptación no bloqueante y cola durable

Cumple para la captura inicial. `POST /api/capturas` responde 202 después de dejar contenido, captura, idempotencia y trabajo durables, sin esperar Transcribe ni Bedrock. La cola registra intentos, backoff, arrendamiento, heartbeat e IDs externos, retoma tras reinicios y limita inicialmente a tres trabajos activos mientras coexisten audio, foto y texto.

### 8. Audio largo y Transcribe por lotes

Cumple. El máximo predeterminado es 300 s y nunca puede configurarse bajo 240 s. MediaRecorder negocia WebM, Ogg, MP4 o M4A, usa `timeslice`, solicita Wake Lock opcional y ofrece selector de archivo; el backend usa `StartTranscriptionJob`/`GetTranscriptionJob` con consulta inicial cada 5 s configurable y umbral operacional de estancamiento, sin topes de 15 o 60 s.

### 9. Transcripción completa, confianza e idiomas

Cumple. `texto_completo` no hereda el límite de 280; ese máximo se aplica a nota y fragmento por niño. Cada palabra conserva confianza, se marca como dudosa bajo 0,60 y registra idioma, proveedor, modelo, identificador y tiempos. El benchmark contempla `es-US`, `es-MX` y `es-ES`, no `es-CL`.

### 10. Modelos, API y control humano

Cumple en nombres, relaciones, campos de captura/S3/duración, transcripción, cola, sugerencias, rechazo de video, detalle, bandeja y prohibición de crear observaciones desde el trabajador. El defecto anterior de `confirmarCaptura` está corregido en `Algoritmo 6`: el retorno para una captura ya `confirmada` ocurre antes de exigir un estado revisable.

**Hallazgo bloqueante, confirmado.** En `Algoritmo 6: corrección y confirmación`, líneas 728-734, `corregirTranscripcion` guarda la versión, invalida sugerencias y ejecuta `encolarBedrockIdempotente`, pero no cambia `captura.estado`. El diagrama, líneas 129 y 134, solo permite que `lista_para_revisar` avance a `confirmada` o `descartada`; no define regreso a `en_cola`/`procesando`. Como `confirmarCaptura` acepta `lista_para_revisar` y `revision_manual` en las líneas 739-741, una confirmación puede competir con el trabajo recién encolado y usar sugerencias invalidadas. La corrección debe restringirse a estados explícitos y, en la misma operación durable que invalida y encola, mover la captura a `en_cola` o `procesando` —o introducir un estado de reprocesamiento—; después deben alinearse diagrama, algoritmo, contrato, endpoint y pruebas.

### 11. Privacidad y seguridad

Cumple. El aviso declara el envío a AWS; H0 verifica permisos S3, Transcribe, Bedrock e IAM sin asumir AWS Organizations. S3 es privado, bloquea acceso público, cifra en reposo, aplica mínimo privilegio, usa claves opacas y URLs breves autorizadas desde backend. La retención predeterminada es de hasta 24 h, producción no persiste nombres en vocabularios y se prohíbe biometría facial o vocal.

### 12. Estados armonizados

**Hallazgo bloqueante, confirmado; mismo defecto del criterio 10.** `esperando_conexion` está aislado en cliente y los estados iniciales coinciden, pero la corrección no tiene transición persistida. Mantener un estado revisable con sugerencias invalidadas permite confirmar antes del nuevo resultado; el subflujo necesita una transición atómica y observable.

### 13. Diagramas, contratos, propiedades, errores y pruebas

**Hallazgo bloqueante, confirmado; mismo defecto del criterio 10.** El diagrama no representa el reprocesamiento prometido por el algoritmo, la especificación formal de `corregirTranscripcion` en la línea 774 y `PUT /api/capturas/{id}/transcripcion` en la línea 1003. Tampoco hay una prueba explícita que impida confirmar entre invalidación y finalización de Bedrock. Los bloques Mermaid tienen sintaxis razonable por inspección; no se ejecutó render, build ni suite.

### 14. Dataset histórico conservado

Cumple. Permanecen siete entidades, reglas históricas, lectura de video, primer ID nuevo, conteos 20/80/500/9/90/2950/8850 y las seis observaciones de `NINO-00002`.

### 15. Sin cambios de implementación ni pruebas ejecutables

Cumple según `git status --short --untracked-files=all`: no aparecen cambios en backend, frontend, pruebas ni código ejecutable. Solo se observaron `.gitignore` y material documental/configuración bajo `.agents/` y `.kiro/`, sin atribuir al editor cambios preexistentes ajenos al documento.

## Alcance y evidencia de la revisión

Se leyeron el documento canónico completo, el plan y la revisión anterior. Una única búsqueda puntual sobre el flujo de corrección confirmó la ausencia de la transición; no se repitieron las verificaciones globales del editor. La evidencia textual del mensaje final del editor no venía incluida como bloque separado en la entrada de esta etapa, así que las conclusiones se apoyan en el documento actual, el plan, la revisión anterior y el estado de Git.

</details>

<details><summary>File map</summary>

- `.kiro/specs/kindergarten-observation-platform/design.md` — documento canónico; requiere armonizar corrección, estado y reprocesamiento.
- `.agents/tasks/design-update-plan.md` — plan contrastado con las decisiones cerradas.
- `.agents/tasks/design-review.md` — informe narrativo editado.
- `.agents/tasks/design-review.json` — veredicto derivado del informe final.

Full diff: `git diff -- .kiro/specs/kindergarten-observation-platform/design.md` no ofrece contenido porque el documento no aparece como archivo rastreado; la fuente revisada es el archivo canónico indicado arriba.

</details>
