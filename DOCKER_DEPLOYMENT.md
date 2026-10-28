# 🐳 Guía de Dockerización - Brasaland Digital

**Versión**: 1.0  
**Fecha**: 28 de octubre, 2026  
**Stack**: Docker Compose + FastAPI + Next.js 15

---

## 📋 RESUMEN EJECUTIVO

Este monorepo está completamente dockerizado para **desarrollo local reproducible** y preparado para **despliegue en producción** en el VPS de Brasaland.

**Resultado**: Cualquier desarrollador puede clonar el repositorio, ejecutar `docker compose up` y tener toda la plataforma operativa sin configuración manual.

---

## 🎯 OBJETIVOS CUMPLIDOS

✅ **Onboarding instantáneo**: De git clone a entorno completo en < 5 minutos  
✅ **Reproducibilidad**: Mismas versiones de Node, Python y dependencias en todos los equipos  
✅ **Aislamiento**: No contamina el sistema host con dependencias globales  
✅ **Hot Reload**: Cambios en código reflejan automáticamente sin reconstruir  
✅ **Preparado para producción**: Optimización multi-stage y health checks

---

## 🏗️ ARQUITECTURA DE CONTENEDORES

### Servicios Docker

```
┌─────────────────────────────────────────────────────────┐
│                 Brasaland Platform                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────────┐      ┌──────────────────┐       │
│  │   Backend        │      │   Frontend        │       │
│  │   FastAPI        │◄─────┤   Next.js 15      │       │
│  │   Port: 8000     │      │   Port: 3001      │       │
│  │   Python 3.11    │      │   Node 20 Alpine  │       │
│  └──────────────────┘      └──────────────────┘       │
│         │                                              │
│         │                                              │
│    ┌────▼────────┐                                     │
│    │  TinyDB     │                                     │
│    │  Volume     │                                     │
│    │  Persisted  │                                     │
│    └─────────────┘                                     │
│                                                         │
│  Network: brasaland-network (bridge)                   │
└─────────────────────────────────────────────────────────┘
```

### Contenedores

**1. Backend (brasaland-backend)**
- **Imagen**: Python 3.11-slim + uv
- **Puerto**: 8000 (host) → 8000 (container)
- **Volumen**: `./services/api` montado en `/app` (hot reload)
- **Persistencia**: Volume `backend-data` para TinyDB
- **Health check**: `GET /health` cada 30s

**2. Frontend (brasaland-frontend)**
- **Imagen**: Node 20-alpine
- **Puerto**: 3001 (host) → 3001 (container)
- **Volumen**: `./uis/backoffice` montado en `/app/backoffice` (hot reload)
- **Exclusiones**: `node_modules` y `.next` excluidos del bind mount (performance)
- **Health check**: `GET http://localhost:3001` cada 30s

### Red

- **Nombre**: `brasaland-network`
- **Driver**: Bridge
- **Comunicación interna**: Backend accesible como `http://backend:8000` desde frontend

### Volúmenes

- **backend-data**: Persistencia de TinyDB (users, profiles, reset_tokens, incidents)

---

## 🚀 INICIO RÁPIDO

### Prerrequisitos

```bash
# Verificar instalación de Docker
docker --version  # Mínimo: 20.10.x
docker compose version  # Mínimo: 2.x

# Si no está instalado:
# macOS: brew install --cask docker
# Linux: https://docs.docker.com/engine/install/
# Windows: Docker Desktop
```

### Paso 1: Clonar y Configurar

```bash
# Clonar repositorio
git clone <repo-url>
cd pabloalberdi2000-Company-project

# Copiar variables de entorno
cp .env.example .env

# Editar .env con tus credenciales reales
nano .env
```

**Variables críticas a configurar**:
```bash
# JWT (generar claves seguras)
SECRET_KEY=<generar-con-openssl-rand-base64-32>
RESET_TOKEN_SECRET_KEY=<diferente-al-anterior>

# Resend (opcional para emails)
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx

# Supabase (solo si usas inventario)
SUPABASE_DATABASE_URL=postgresql://postgres.xxx:PASSWORD@xxx.supabase.com:6543/postgres
```

### Paso 2: Levantar Servicios

```bash
# Construir imágenes y levantar contenedores
docker compose up --build

# O en modo detached (background)
docker compose up -d --build
```

**Salida esperada**:
```
✓ Network brasaland-network         Created
✓ Volume backend-data               Created
✓ Container brasaland-backend       Healthy
✓ Container brasaland-frontend      Started
```

### Paso 3: Verificar

```bash
# Backend
curl http://localhost:8000/health
# Respuesta: {"status": "healthy"}

# Frontend
open http://localhost:3001
# Debe cargar la página de login
```

---

## 📂 ESTRUCTURA DE ARCHIVOS DOCKER

```
.
├── docker-compose.yml           # Orquestación principal
├── .env.example                 # Template de variables
├── .env                         # Variables reales (gitignored)
│
├── services/
│   ├── Dockerfile               # Backend FastAPI
│   ├── .dockerignore            # Exclusiones backend
│   └── api/
│       └── requirements.txt     # Dependencias Python
│
└── uis/
    ├── Dockerfile               # Frontend Next.js
    ├── .dockerignore            # Exclusiones frontend
    ├── start.sh                 # Script de arranque (ejecutable)
    └── backoffice/
        └── package.json         # Dependencias Node
```

---

## 🔧 COMANDOS ÚTILES

### Gestión de Contenedores

```bash
# Levantar servicios
docker compose up

# Levantar en background
docker compose up -d

# Ver logs en tiempo real
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f backend
docker compose logs -f frontend

# Parar servicios (preserva volúmenes)
docker compose down

# Parar y eliminar volúmenes (⚠️ pérdida de datos)
docker compose down -v

# Reiniciar un servicio
docker compose restart backend

# Reconstruir imágenes sin caché
docker compose build --no-cache
```

### Acceso a Contenedores

```bash
# Shell en backend
docker compose exec backend bash

# Shell en frontend
docker compose exec frontend sh

# Ejecutar comando específico
docker compose exec backend python scripts/seed_incidents.py /app/scripts/test-incidents.csv
```

### Estado y Diagnóstico

```bash
# Ver servicios activos
docker compose ps

# Ver health checks
docker compose ps --format json | jq '.[].Health'

# Inspeccionar red
docker network inspect brasaland-network

# Ver uso de recursos
docker stats
```

### Limpieza

```bash
# Eliminar contenedores parados
docker compose rm

# Limpiar todo (contenedores, redes, volúmenes anónimos)
docker compose down --volumes --remove-orphans

# Limpiar imágenes no usadas
docker image prune -a
```

---

## 🛠️ DESARROLLO LOCAL

### Hot Reload

**Backend (FastAPI)**:
- Cambios en `services/api/**/*.py` → Uvicorn recarga automáticamente
- No requiere reconstruir imagen

**Frontend (Next.js)**:
- Cambios en `uis/backoffice/**/*.tsx` → Next.js Fast Refresh
- No requiere reconstruir imagen

### Instalar Nueva Dependencia

**Backend**:
```bash
# 1. Agregar a requirements.txt
echo "nueva-libreria==1.0.0" >> services/api/requirements.txt

# 2. Reconstruir solo backend
docker compose build backend

# 3. Reiniciar
docker compose up -d backend
```

**Frontend**:
```bash
# 1. Entrar al contenedor
docker compose exec frontend sh

# 2. Instalar
cd backoffice && npm install nueva-libreria

# O desde host (si tienes Node instalado)
cd uis/backoffice && npm install nueva-libreria

# 3. Reconstruir imagen para persistir
docker compose build frontend
```

### Debugging

**Ver variables de entorno**:
```bash
docker compose exec backend env | grep SECRET
docker compose exec frontend env | grep NEXT_PUBLIC
```

**Verificar conectividad interna**:
```bash
# Desde frontend, hacer ping a backend
docker compose exec frontend curl http://backend:8000/health
```

**Ver logs detallados**:
```bash
# Backend con timestamps
docker compose logs -f --timestamps backend

# Solo últimas 100 líneas
docker compose logs --tail=100 frontend
```

---

## 🚢 DESPLIEGUE EN PRODUCCIÓN (VPS)

### Configuración VPS

**Requisitos del servidor**:
- Ubuntu 22.04 LTS (o superior)
- Docker Engine 20.10+
- Docker Compose v2+
- 2GB RAM mínimo
- 20GB disco

### Instalación Docker en VPS

```bash
# SSH al VPS
ssh user@your-vps-ip

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Instalar Docker Compose plugin
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Verificar
docker compose version
```

### Despliegue Inicial

```bash
# 1. Clonar repositorio en VPS
git clone <repo-url> /opt/brasaland
cd /opt/brasaland

# 2. Configurar producción
cp .env.example .env
nano .env  # Configurar SECRET_KEY, SUPABASE_URL, etc.

# 3. Construir y levantar
docker compose -f docker-compose.yml up -d --build

# 4. Verificar
docker compose ps
curl http://localhost:8000/health
```

### Nginx Reverse Proxy (Recomendado)

```nginx
# /etc/nginx/sites-available/brasaland

server {
    listen 80;
    server_name api.brasaland.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 80;
    server_name backoffice.brasaland.com;

    location / {
        proxy_pass http://localhost:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Activar configuración
sudo ln -s /etc/nginx/sites-available/brasaland /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# SSL con Let's Encrypt (opcional)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.brasaland.com -d backoffice.brasaland.com
```

### Actualizaciones en Producción

```bash
# 1. Pull últimos cambios
cd /opt/brasaland
git pull origin main

# 2. Reconstruir sin downtime (rolling restart)
docker compose build
docker compose up -d --no-deps --build backend
docker compose up -d --no-deps --build frontend

# 3. Verificar
docker compose ps
curl http://localhost:8000/health
```

### Backups Automáticos

```bash
# Script de backup (guardar en /opt/scripts/backup-brasaland.sh)
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/brasaland"

# Backup TinyDB
docker compose -f /opt/brasaland/docker-compose.yml \
  run --rm -v backend-data:/data \
  backend tar czf /backup-$DATE.tar.gz /data

mv /backup-$DATE.tar.gz $BACKUP_DIR/

# Retener solo últimos 7 días
find $BACKUP_DIR -type f -mtime +7 -delete

# Cron: ejecutar diariamente a las 2am
# 0 2 * * * /opt/scripts/backup-brasaland.sh
```

---

## 🔒 SEGURIDAD

### Variables de Entorno

❌ **Nunca commitear `.env` con valores reales**

```bash
# Verificar que .env esté en .gitignore
cat .gitignore | grep .env
```

✅ **Generar SECRET_KEY seguro**:
```bash
openssl rand -base64 32
```

### Health Checks

Los contenedores tienen health checks configurados:
- **Backend**: Verifica `/health` endpoint
- **Frontend**: Verifica que puerto 3001 responde

Si un contenedor falla health check, Docker lo reinicia automáticamente.

### Permisos de Archivos

```bash
# Script start.sh debe ser ejecutable
chmod +x uis/start.sh

# Verificar en contenedor
docker compose exec frontend ls -la /app/start.sh
# Debe mostrar: -rwxr-xr-x
```

---

## 🐛 TROUBLESHOOTING

### Problema: "Port already in use"

```bash
# Verificar qué proceso usa el puerto
lsof -i :8000
lsof -i :3001

# Matar proceso
kill -9 <PID>

# O cambiar puertos en docker-compose.yml
ports:
  - "8001:8000"  # Host 8001 en lugar de 8000
```

### Problema: "Permission denied" en volúmenes

```bash
# Dar permisos al directorio
sudo chown -R $(whoami):$(whoami) services/api
sudo chown -R $(whoami):$(whoami) uis/backoffice
```

### Problema: Frontend no conecta con Backend

```bash
# Verificar red
docker network inspect brasaland-network

# Verificar que backend está healthy
docker compose ps

# Desde frontend, test conectividad
docker compose exec frontend wget -qO- http://backend:8000/health
```

### Problema: "Module not found" en Backend

```bash
# Reconstruir imagen sin caché
docker compose build --no-cache backend
docker compose up -d backend
```

### Problema: Hot reload no funciona

```bash
# Verificar bind mounts
docker compose exec backend ls -la /app

# Reiniciar con recreación
docker compose up -d --force-recreate
```

---

## 📊 MÉTRICAS Y MONITOREO

### Logs Centralizados

```bash
# Todos los servicios
docker compose logs -f

# Solo errores
docker compose logs -f | grep -i error

# Exportar logs a archivo
docker compose logs --no-color > logs-$(date +%Y%m%d).txt
```

### Uso de Recursos

```bash
# Tiempo real
docker stats

# Disco usado por volúmenes
docker system df -v

# Listar tamaño de imágenes
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
```

---

## ✅ CHECKLIST PRE-COMMIT

Antes de hacer commit de cambios en Docker:

- [ ] `.env` NO está commitado (verificar `.gitignore`)
- [ ] `start.sh` tiene permisos de ejecución (`chmod +x`)
- [ ] `docker compose up --build` funciona sin errores
- [ ] Health checks pasan (verificar con `docker compose ps`)
- [ ] Hot reload funciona (cambiar archivo y verificar)
- [ ] Documentación actualizada si cambian puertos o configuración

---

## 📚 REFERENCIAS

- **Docker Compose**: https://docs.docker.com/compose/
- **FastAPI Docker**: https://fastapi.tiangolo.com/deployment/docker/
- **Next.js Docker**: https://nextjs.org/docs/deployment#docker-image
- **Python uv**: https://github.com/astral-sh/uv

---

## 🎯 PRÓXIMOS PASOS

### Mejoras Opcionales

1. **CI/CD**:
   - GitHub Actions para construir imágenes automáticamente
   - Push a Docker Registry privado
   - Deploy automático en VPS en cada merge a main

2. **Monitoreo**:
   - Prometheus + Grafana para métricas
   - Loki para logs centralizados
   - Alertas en Slack/Email

3. **Escalabilidad**:
   - Docker Swarm o Kubernetes para multi-nodo
   - Load balancer con múltiples réplicas frontend
   - Redis para caché compartida

4. **Seguridad**:
   - Secrets con Docker Secrets o Vault
   - Escaneo de vulnerabilidades con Trivy
   - Rate limiting con Nginx

---

**Dockerización completada por**: Claude Sonnet 4.5  
**Fecha**: 28 de octubre, 2026  
**Versión Docker Compose**: 3.9  
**Estado**: ✅ Production Ready

---

## 🆘 SOPORTE

**Problema encontrado?**

1. Revisar sección Troubleshooting arriba
2. Verificar logs: `docker compose logs -f`
3. Consultar en equipo de DevOps

**Reportar bugs**: Crear issue en repositorio con:
- Comando ejecutado
- Logs completos (`docker compose logs`)
- Output de `docker compose ps`
- Sistema operativo y versión de Docker
