# Imagen única: compila el frontend y lo sirve junto a la API (un solo link).

# ---- Etapa 1: build del frontend (React + Vite) ----
FROM node:24-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Etapa 2: API FastAPI que también sirve la app web ----
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/app backend/app
COPY Dump/dataset_e1_publico/datos_publicos Dump/dataset_e1_publico/datos_publicos
COPY --from=frontend /build/dist frontend/dist

# Corre sin privilegios de root.
RUN useradd --create-home --uid 10001 app
USER app

WORKDIR /srv/backend
EXPOSE 8000
# Render define PORT al arrancar el contenedor; en local se usa 8000.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
