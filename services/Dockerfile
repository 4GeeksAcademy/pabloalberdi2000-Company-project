# ============================================
# Multi-stage Dockerfile para Backend FastAPI
# Brasaland Digital Platform
# ============================================

# Stage 1: Base con uv y dependencias del sistema
FROM python:3.11-slim AS base

# Metadata
LABEL maintainer="Brasaland Digital Team"
LABEL description="FastAPI Backend - ATS, Incidents & Inventory System"

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv (gestor de paquetes moderno de Python)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:/root/.cargo/bin:$PATH"

# Crear directorio de trabajo
WORKDIR /app

# Stage 2: Dependencias
FROM base AS dependencies

# Copiar requirements.txt
COPY services/api/requirements.txt /app/requirements.txt

# Instalar dependencias normales (sin el paquete compartido)
RUN grep -v "^-e" requirements.txt > requirements_filtered.txt && \
    pip install --no-cache-dir -r requirements_filtered.txt

# Stage 3: Aplicación
FROM dependencies AS application

# Copiar paquete compartido
COPY packages/shared/python /packages/shared/python

# Instalar paquete compartido
RUN pip install -e /packages/shared/python

# Copiar código del backend
COPY services/api/ /app/

# Crear directorios necesarios
RUN mkdir -p /app/logs

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
