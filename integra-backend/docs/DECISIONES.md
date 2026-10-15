# Decisiones (para discutir en equipo)

Alcance de esta etapa: **una Lambda que recibe una nota y la procesa con LLM**, con datos en DynamoDB y S3. Nada de
API, frontend ni orquestación. Cada decisión dice qué cambia si el equipo elige otra cosa.

| # | Decisión | Recomendado | Estado |
|---|---|---|---|
| D1 | Dónde viven los datos | DynamoDB (nómina y resultados) + S3 (rúbrica) | ⬜ por discutir |
| D2 | Cómputo | 1 Lambda síncrona | ⬜ por discutir |
| D3 | RAG | Embeddings de la rúbrica en S3, búsqueda en memoria | ⬜ por discutir |
| D4 | Modelos | Haiku 4.5 (separar) + Sonnet 5 (conductas, nivel), 3 corridas | ⬜ por discutir |
| D5 | Infraestructura como código | AWS SAM | ⬜ por discutir |
| D6 | Edad | Sin ventana: se busca en toda la rúbrica; la edad solo se compara en código | ✅ acordado |
| D7 | Región | us-east-1 | ⬜ confirmar con la organización |
| D8 | Qué produce el LLM | Solo el código de manifestación; nivel, dominio y texto por cruce con `rubrica.json` | ✅ acordado |

## D1. Datos: DynamoDB + S3
- **DynamoDB** guarda lo que se consulta por clave: educadoras (para saber el jardín), niños/as por jardín (la nómina, con
  nombres y apodos) y las observaciones resultantes (cada fragmento como su propio registro). Sin servidor, sin red que
  configurar, pago por uso.
- **S3** guarda archivos: la rúbrica, los embeddings de la rúbrica y el dataset original. Cambiar la rúbrica es
  subir un archivo nuevo, sin redeploy.
- Alternativa: todo en S3 (JSON) → más simple aún, pero guardar y consultar observaciones se vuelve incómodo.
- Alternativa: Aurora PostgreSQL → SQL libre, pero obliga a VPC y más montaje.

## D2. Una Lambda síncrona
Todo el pipeline en una función (timeout 5 min), probada con `sam remote invoke` o un evento de prueba en la consola.
**Después** (no ahora): exponerla con una URL o API Gateway, y si las notas largas tardan mucho, pasar a Step Functions.

## D3. RAG sin servicios extra
La rúbrica tiene 90 manifestaciones: los embeddings (Titan V2) se calculan una vez, se guardan en S3 y la Lambda compara en
memoria, sobre las 90 manifestaciones (sin filtro por edad). **Después** se puede migrar a Bedrock Knowledge Base + S3 Vectors
(misma interfaz `Retriever`) si se quiere mostrar en el pitch o agregar los PDF de Integra.

## D4. Modelos
En Bedrock están disponibles **Claude Haiku 4.5** y **Claude Sonnet 5**. Haiku 4.5 para separar e identificar (rápido);
Sonnet 5 para conductas y nivel (requiere más criterio). La evaluación de nivel corre 3 veces y la certeza sale del acuerdo.
Si Haiku falla con nombres difíciles en el checkpoint, se usa Sonnet 5 también para separar (solo cambia una variable).
Kiro puede usar otros modelos para escribir el código; eso es independiente de Bedrock.

## D5. AWS SAM
Un `template.yaml` con 6 recursos; `sam build` / `sam deploy`. Alternativa: crear todo por consola (sirve, pero no se
puede rehacer fácil).

## D6. Edad (acordado)
Se descartó filtrar por tramo o ventana de edad: los niveles lejanos no se confunden y la ventana podía esconder justo los
rezagos más grandes (un niño dos niveles abajo ni siquiera aparecía entre las candidatas). El LLM busca en toda la rúbrica y
usa juntas `ruta_niveles` (descripción del nivel) y `manifestaciones` (evidencia). La edad (exacta, desde la fecha de
nacimiento) solo se usa en código, después, para comparar con los niveles esperados de `ruta_niveles`. Cuando llegue la
rúbrica real de Integra (por nivel educativo), el nivel educativo servirá solo para elegir cuál rúbrica usar.
Salida por dominio: `nivel` + `certeza` + `comentario` (por qué ese nivel, si otro es viable y la nota de edad). Es solo una
sugerencia: la tía la acepta, cambia o descarta. No evaluable → `nivel = null` (no "nivel 0").

## D7. Región
us-east-1 por disponibilidad de modelos. Confirmar si la cuenta del evento limita regiones.

## D8. El LLM elige el código; el resto es un cruce (acordado)
El LLM devuelve solo `id_manifestacion` (restringido a los 90 por el esquema). Nivel, dominio y texto_observable salen de
`data/processed/rubrica.json` con un diccionario: no hay IA que se pueda equivocar en eso. El prompt usa 9 ejemplos
(`fewshot.json`, 1 por nivel). La medición (`validacion_100.json`, 11–12 casos por nivel) usa observaciones, niños y
códigos que NO aparecen en el few-shot (verificado: 0 superposición). Métrica principal: accuracy del código.

## Para después (fuera de esta etapa)
API Gateway o URL de la función · conexión con el frontend · validación de la tía · Step Functions · Knowledge Base ·
carga del historial de observaciones · métricas de precisión · Cognito.

## Preguntas abiertas para Integra
(Se refieren a la rúbrica REAL de Integra, de 8 niveles. El sistema actual usa la rúbrica E-1 de 9 niveles y lee todo desde `rubrica.json`.)
1. ¿Nos pasan la rúbrica real (núcleos × 8 niveles × tramos, con conductas observables)?
2. ¿Los 8 niveles son una escala por tramo o continua entre tramos?
3. ¿Cómo manejan las salas heterogéneas?
