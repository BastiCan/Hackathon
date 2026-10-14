# Integra · Desafío 1 — IA para el Desarrollo Infantil

Aplicación para educadoras de párvulos de Fundación Integra que reduce el tiempo de
documentación pedagógica y ayuda a **detectar rezagos a tiempo**.

> Hackatón AWS Breaking Barriers Chile 2026 (14–16 oct, FCFM U. de Chile).

## El problema

Hoy una educadora dedica ~4 horas semanales a sistematizar observaciones (pasar notas
de post-its y cuadernos a núcleos y niveles). El objetivo es llevar ese tiempo lo más
cerca posible de 0, manteniendo a la educadora como quien **decide**: la IA solo sugiere.

## Qué hace la app

1. **Captura rápida** en sala: audio (prioritario), foto, texto.
2. **Procesamiento con IA**: transcribe, separa observaciones por niño, filtra lo no
   evaluable y **sugiere** núcleo, manifestación y nivel con la evidencia textual.
3. **Validación**: la educadora acepta o corrige en una bandeja de pendientes.
4. **Seguimiento**: vista de sala con semáforo, ficha por niño con línea de tiempo,
   alertas de rezago y "misión del día".

Ver la propuesta completa en [`Dump/integra_desafio1_sintesis.md`](Dump/integra_desafio1_sintesis.md).

## Arquitectura

| Capa | Stack | Carpeta |
|---|---|---|
| Frontend | React + Vite + TypeScript (PWA) | [`frontend/`](frontend/) |
| Backend | FastAPI (Python 3.13) | [`backend/`](backend/) |
| Datos | Dataset sintético E-1 (CSV / JSON) | [`Dump/dataset_e1_publico/`](Dump/dataset_e1_publico/) |
| IA | Capa de servicio con interfaz estable (mock → modelo real) | [`backend/app/services/ai.py`](backend/app/services/ai.py) |
| Despliegue | Una imagen Docker en Render (plan gratis): la API también sirve las pantallas | [`Dockerfile`](Dockerfile), [`render.yaml`](render.yaml) |

## Ver la app en línea (un solo link)

La app se despliega en [Render](https://render.com) como un único servicio: pantallas y
API quedan bajo la misma URL. Configuración inicial, una sola vez:

1. Entra a [render.com](https://render.com) con **Sign in with GitHub**.
2. Abre <https://render.com/deploy?repo=https://github.com/BastiCan/Hackathon>.
   Si Render pide permisos, instala su GitHub App y dale acceso al repo `Hackathon`
   (es privado).
3. Confirma el Blueprint (servicio `integra-hackathon`, plan Free) y espera el primer
   build (~5 min). Cuando diga **Live**, el link aparece arriba del servicio
   (`https://integra-hackathon….onrender.com`).

Después, cada push a `main` redespliega solo.

- En el plan gratis el servicio se duerme tras 15 min sin visitas y despierta en
  ~1 min con la siguiente. Antes de una demo, abre el link un minuto antes.
- La app no tiene login: cualquiera con el link la ve. Sirve porque los datos son
  sintéticos; con datos reales de niños hay que agregar autenticación primero.

## Puesta en marcha

Requisitos: Python 3.13+, Node.js 20+.

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
# API en http://localhost:8000  ·  docs en http://localhost:8000/docs
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
# App en http://localhost:5173
```

### Todo en un solo servidor (más liviano)

Si ya existe `frontend/dist` (`npm run build`), el backend también sirve la app web y no
hace falta el servidor de Vite:

```powershell
cd frontend; npm run build; cd ..\backend
uvicorn app.main:app
# App y API en http://localhost:8000
```

## Estructura del repositorio

```
Hackaton/
├─ backend/              API FastAPI + carga del dataset + capa de IA
├─ frontend/             PWA React para la educadora
├─ Dump/                 Material del desafío (síntesis + dataset sintético)
├─ Dockerfile            Imagen única: build del frontend + API
├─ render.yaml           Blueprint de despliegue en Render
└─ README.md
```

## Datos y privacidad

- El dataset es **100% sintético**; no contiene datos reales de niños.
- Los PDFs de referencia (Referente Curricular, Modelo de Educación Emocional) tienen
  copyright de Integra/MINEDUC y **no se versionan** en el repositorio (ver `.gitignore`).
- Diseño pensado para seudonimización y borrado automático de multimedia (Ley 21.719).
