---
inclusion: always
---
# Producto: procesador de notas de sala con LLM (Desafío 1 · Fundación Integra)

## Contexto
Una tía (educadora o técnica de párvulos) dedica ~4 horas semanales a pasar sus notas de sala a núcleos y niveles.
Otro equipo convierte fotos de post-its/audios en texto. **Este proyecto parte cuando ya existe el texto.**

## Qué hace (alcance COMPLETO de esta etapa)
Una función en AWS recibe una nota en texto libre + quién la envía (`id_educadora`) + de qué sala viene (`sala_grupo`) + fecha, y:

1. **Separa** la nota con un LLM: cuáles fragmentos son **generales** (del grupo) y cuáles son **particulares** (de un niño/a),
   y **guarda cada uno como su propio texto** en DynamoDB.
2. **Identifica** al niño/a de cada fragmento particular cruzando el nombre con los niños/as de la sala (deducidos de la
   educadora y la sala). **Si no se puede resolver, devuelve un error para ese fragmento** (no adivina).
3. Para cada fragmento particular identificado, decide si es **evaluable** y hace **RAG sobre la rúbrica** para sugerir
   el **nivel** obtenido (con dominio, certeza y un comentario que explica la decisión y si otro nivel es viable), buscando en toda la rúbrica.
   Después, en código, compara el nivel con lo esperado para la edad del niño/a (`ruta_niveles`).

## Ubicación en el repo
Este proyecto vive en la carpeta `integra-backend/` del repo del equipo `BastiCan/Hackathon`. **Todo el trabajo se hace dentro
de `integra-backend/`.** El resto del repo (`backend/` con FastAPI, `frontend/`, `Dump/`, `Dockerfile`, `render.yaml`) es un
espacio de ideas de otros integrantes: no leerlo como referencia, no reutilizar su código y no modificarlo.

## Entrada del sistema
El texto que se clasifica es **siempre lo escrito por las tías** (notas, post-its transcritos, audios transcritos). Nunca el
texto de la rúbrica (`texto_observable`) ni la descripción de los niveles: esos son conocimiento de referencia del clasificador.

## Fuera de alcance por ahora (NO construir)
API Gateway, endpoints, frontend, validación por la tía, Step Functions, Cognito, Knowledge Base gestionada,
carga del historial de observaciones, métricas. Se verán después. Si una tarea parece necesitarlos, preguntar.

## Principios
- **La IA sugiere**: todo queda como `SUGERIDO`.
- **No inventar**: si no se identifica al niño/a o falta detalle para el nivel, se dice explícitamente.
- **Inclinarse a evaluable** ante la duda.
- **Datos ya anonimizados**: la base de datos ya viene anonimizada; no construir seudonimización adicional. No escribir el texto de las notas en logs.
- **La edad NO se le entrega al LLM**: solo se usa en código después de evaluar (ver `dominio.md` §1).

## Datos
Dataset sintético E-1 en `data/raw/` (500 niños/as, 20 jardines, 80 educadoras, rúbrica de 9 niveles × 5 dominios).
Está anonimizado (solo IDs): para probar la identificación por nombre se usan nombres de demo sobre niños/as reales de JAR-0001 (`tests/fixtures/nomina_demo.json`); no generar más. La rúbrica es configuración (se reemplazará por la
rúbrica real de Integra).
