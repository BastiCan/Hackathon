# Integra · Desafío 1: IA para documentar el desarrollo infantil

Hackatón AWS Breaking Barriers Chile 2026 (14–16 oct, FCFM U. de Chile) · Desafío 1 de Fundación Integra.

Hoy una educadora dedica cerca de 4 horas a la semana a pasar post-its y cuadernos a la ruta de aprendizaje
de cada niño. **Huellita** busca bajar ese tiempo a menos de 15 minutos: la tía registra en 2 toques (foto de
post-its, audio o texto) y la IA sugiere a qué niño corresponde, qué conducta se observó y en qué nivel va,
citando la evidencia.

- **La IA sugiere y la tía decide:** ella confirma, corrige o descarta cada sugerencia.
- **Sin lenguaje de diagnóstico:** la ruta no es un instrumento clínico y la falta de registro no significa
  falta de aprendizaje. En pantalla se habla de "sin registro reciente", nunca de "rezago".

## Demo

**<https://bastican.github.io/Hackathon/>**: Huellita con datos ficticios e IA simulada (no se conecta a AWS).
Es el mismo archivo que [`huellita-formato-mejorado/huellita-demo.html`](huellita-formato-mejorado/huellita-demo.html),
que también funciona con doble clic.

## Qué hay en el repositorio

| Carpeta | Qué es | Estado |
|---|---|---|
| [`huellita-formato-mejorado/`](huellita-formato-mejorado/) | App de las tías: React + Vite + TypeScript (PWA). Inicio para registrar (foto, grabar audio, escribir y subir audio, con selector de sala), planilla de la sala con un color por nivel, revisión de sugerencias, ficha por niño y vista de directora. Usa la rúbrica del backend (5 núcleos × 9 niveles). | Versión actual. Funciona con datos locales e IA simulada; los servicios de datos e IA están separados para conectarla a un backend. |
| [`huellita/`](huellita/) | Versión anterior de Huellita (diseño de post-its). | Referencia, sin cambios. |
| [`integra-backend/`](integra-backend/) | Procesamiento con IA en AWS: Lambda en Python 3.13 con Amazon Bedrock, DynamoDB y S3 (AWS SAM). | Procesa las capturas que llegan a S3 y guarda observaciones sugeridas. Todavía no tiene API para el frontend. |
| [`servicio_transcripcion/`](servicio_transcripcion/) | Transcripción de audio en AWS: Lambda (FastAPI) detrás de API Gateway REST, Amazon Transcribe por lotes y EventBridge (AWS SAM). | Desplegado como stack `transcriptor-audio` en us-east-1 y probado de punta a punta: deja el audio y `texto.json` en `integra-capturas`, lo que activa `ProcesarNota`. |
| [`Dump/`](Dump/) | Material del desafío: [síntesis](Dump/integra_desafio1_sintesis.md) y [dataset sintético E-1](Dump/dataset_e1_publico/). | — |
| `backend/`, `frontend/`, `ver-app.bat`, `Dockerfile`, `render.yaml` | Primer prototipo (FastAPI + React, con una IA de prueba basada en reglas). | Reemplazado por Huellita e integra-backend. Queda solo como referencia. |

## Cómo funciona el procesamiento (`integra-backend`)

1. Cada captura se sube a S3 en `capturas/CAP-<ULID>/`: primero `meta.json` (educadora, sala y fecha) y al
   final `texto.json` (una parte por post-it o nota).
2. La llegada de `texto.json` dispara la Lambda `ProcesarNota`, que:
   - separa lo que es de un niño de lo que es de toda la sala;
   - identifica al niño por nombre o apodo dentro de su sala. Si hay dudas (dos niños con el mismo nombre, o
     uno de otra sala) no lo asigna y deja los candidatos;
   - decide si la nota es evaluable y busca en la rúbrica las manifestaciones que la respaldan (RAG con embeddings);
   - sugiere el nivel con su certeza (alta, media o baja).
3. El resultado queda en DynamoDB: las observaciones en `Observaciones` (estado `SUGERIDO`) y el avance de cada
   captura en `Registros`.

Más detalle en `integra-backend/`: diseño y contrato en
[`.kiro/specs/backend-observaciones/design.md`](integra-backend/.kiro/specs/backend-observaciones/design.md),
montaje y pruebas en [`docs/AWS_SETUP.md`](integra-backend/docs/AWS_SETUP.md) y decisiones en
[`docs/DECISIONES.md`](integra-backend/docs/DECISIONES.md).

## Pendiente para conectar todo

- Una API con login (Cognito) entre Huellita y el backend: leer salas, niños y sugerencias, confirmar o corregir,
  y subir capturas.
- ~~Unificar la rúbrica.~~ Hecho: Huellita usa la misma del backend (dataset E-1, 9 niveles × 5 dominios,
  90 manifestaciones); `huellita-formato-mejorado/data/rubrica_e1.json` es copia exacta y una prueba avisa si
  se desalinean.
- Unificar la nómina de demo (nombres inventados sobre los IDs del dataset) para la app, el backend y las fotos
  de prueba.
- La lectura de fotos de post-its (OpenCV + Bedrock), que se está desarrollando aparte.
- Que la app suba los audios al transcriptor (`servicio_transcripcion/`) y escriba el `meta.json` de cada captura en `integra-capturas` antes de que termine la transcripción.

## Puesta en marcha

### Huellita

Requisitos: Node.js 20 o superior.

```powershell
cd huellita-formato-mejorado
npm install
npm run dev     # http://localhost:5173
npm test        # pruebas con Vitest
```

### integra-backend

Requisitos: Python 3.13. Las pruebas unitarias corren sin AWS. El pipeline llama a Bedrock, así que necesita
credenciales y los IDs de modelo (ver [`docs/AWS_SETUP.md`](integra-backend/docs/AWS_SETUP.md)).

```powershell
cd integra-backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m pytest tests/unit -q

# Con credenciales de AWS y los MODEL_ID_* configurados (copia .env.example a .env):
python scripts/pipeline_local.py --texto "Pedro y Emilio clasificaron hojas por tamaño" --educadora EDU-0001 --sala SG-A
```

El despliegue usa `sam build` y `sam deploy --guided`. Los pasos completos, la carga de datos y la prueba con una
captura están en `docs/AWS_SETUP.md`.

### Primer prototipo

Doble clic en `ver-app.bat`. Necesita `backend/.venv` y `frontend/dist`; si falta alguno, el script avisa qué correr.

## Datos y privacidad

- El dataset es 100% sintético y los nombres de los niños en las demos son inventados.
- Los PDFs de referencia (Referente Curricular, Modelo de Educación Emocional) tienen copyright y no se versionan
  (ver `.gitignore`).
- Todavía no hay login: la demo publicada solo muestra datos ficticios. Antes de usar datos reales hay que agregar
  autenticación y control de acceso por rol.
- Las credenciales de AWS van como variables de entorno o en `.env` (ignorado por git), nunca en el repositorio.
