# ============================================
# Multi-stage Dockerfile para Frontend Next.js
# Brasaland Digital Platform
# ============================================

# Stage 1: Base con Node.js Alpine
FROM node:20-alpine as base

# Metadata
LABEL maintainer="Brasaland Digital Team"
LABEL description="Next.js Frontend - Backoffice"

# Instalar dependencias del sistema necesarias
RUN apk add --no-cache \
    libc6-compat \
    curl

# Crear directorio de trabajo
WORKDIR /app

# Stage 2: Dependencias
FROM base as dependencies

# Copiar package.json de backoffice
COPY backoffice/package.json backoffice/package-lock.json* ./backoffice/

# Instalar dependencias de backoffice
RUN cd backoffice && npm ci --only=production=false

# Stage 3: Desarrollo
FROM base as development

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
