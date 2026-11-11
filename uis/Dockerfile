# ============================================
# Multi-stage Dockerfile para Frontend Next.js
# Brasaland Digital Platform
# ============================================

# Stage 1: Base con Node.js
FROM node:20-slim AS base

# Metadata
LABEL maintainer="Brasaland Digital Team"
LABEL description="Next.js Frontend - Backoffice"

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Stage 2: Dependencias
FROM base AS dependencies

# Copiar package.json de backoffice
COPY backoffice/package.json backoffice/package-lock.json* ./backoffice/

# Instalar dependencias de backoffice
RUN cd backoffice && npm ci --only=production=false

# Stage 3: Desarrollo
FROM base AS development

# Copiar node_modules desde stage de dependencias
COPY --from=dependencies /app/backoffice/node_modules ./backoffice/node_modules

# Copiar código fuente de backoffice
COPY backoffice/ ./backoffice/

# Copiar script de arranque
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Exponer puertos
# Backoffice: 3001
EXPOSE 3001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:3001 || exit 1

# Comando por defecto: ejecutar script de arranque
CMD ["/app/start.sh"]
