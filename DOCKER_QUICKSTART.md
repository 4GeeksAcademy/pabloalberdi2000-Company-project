# 🐳 Docker Quick Start - Brasaland

**Guía ultra-rápida** para desarrolladores nuevos en el proyecto.

---

## ⚡ TL;DR

```bash
# 1. Clonar
git clone <repo-url>
cd pabloalberdi2000-Company-project

# 2. Configurar
cp .env.example .env
# Editar .env con tus credenciales (SECRET_KEY, SUPABASE_DATABASE_URL)

# 3. Levantar
docker compose up --build

# 4. Acceder
# Backend: http://localhost:8000
# Frontend: http://localhost:3001
```

**Listo** ✅ Ya tienes todo el stack corriendo.

---

## 🎯 URLs de Acceso

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Backend API** | http://localhost:8000 | FastAPI REST API |
| **API Docs** | http://localhost:8000/docs | Swagger UI interactivo |
| **Frontend Backoffice** | http://localhost:3001 | Next.js 15 App Router |
| **Health Check** | http://localhost:8000/health | Status del backend |

---

## 🔑 Variables de Entorno Críticas

**Mínimo para levantar**:
```bash
# .env
SECRET_KEY=your-secret-key-min-32-chars
RESET_TOKEN_SECRET_KEY=different-secret-min-32-chars
```

**Opcional (para funcionalidades específicas)**:
```bash
RESEND_API_KEY=re_xxx                    # Para emails de reset password
SUPABASE_DATABASE_URL=postgresql://...   # Para sistema de inventario
```

---

## 🛠️ Comandos Más Usados

```bash
# Levantar (primera vez)
docker compose up --build

# Levantar en background
docker compose up -d

# Ver logs en tiempo real
docker compose logs -f

# Ver logs solo del backend
docker compose logs -f backend

# Ver logs solo del frontend
docker compose logs -f frontend

# Parar todo
docker compose down

# Parar y eliminar volúmenes (⚠️ borra TinyDB)
docker compose down -v

# Reiniciar un servicio
docker compose restart backend

# Entrar a shell del backend
docker compose exec backend bash

# Entrar a shell del frontend
docker compose exec frontend sh

# Ver estado de servicios
docker compose ps
```

---

## 🔧 Tareas Comunes

### Instalar Dependencia Python

```bash
# 1. Agregar a requirements.txt
echo "fastapi-cache==0.1.0" >> services/api/requirements.txt

# 2. Reconstruir backend
docker compose build backend

# 3. Reiniciar
docker compose up -d backend
```

### Instalar Dependencia Node

```bash
# Desde host (si tienes Node)
cd uis/backoffice
npm install axios

# Reconstruir frontend
docker compose build frontend
docker compose up -d frontend
```

### Ejecutar Script de Seeding

```bash
docker compose exec backend python scripts/seed_incidents.py /app/scripts/test-incidents.csv
```

### Ver Variables de Entorno

```bash
# Backend
docker compose exec backend env | grep SECRET

# Frontend
docker compose exec frontend env | grep NEXT_PUBLIC
```

---

## 🐛 Problemas Comunes

### Error: "Port already in use"

```bash
# Matar proceso que usa el puerto
lsof -i :8000  # Backend
lsof -i :3001  # Frontend
kill -9 <PID>
```

### Error: "Module not found" en Backend

```bash
# Reconstruir sin caché
docker compose build --no-cache backend
docker compose up -d backend
```

### Frontend no conecta con Backend

```bash
# Verificar que backend está healthy
docker compose ps

# Test desde frontend
docker compose exec frontend curl http://backend:8000/health
```

### Hot Reload no funciona

```bash
# Recrear contenedores
docker compose up -d --force-recreate
```

---

## 📦 Estructura Simplificada

```
.
├── docker-compose.yml          # ← Orquestación principal
├── .env                        # ← Tus credenciales (NO commitear)
│
├── services/
│   ├── Dockerfile              # ← Backend FastAPI
│   └── api/                    # ← Código Python
│
└── uis/
    ├── Dockerfile              # ← Frontend Next.js
    ├── start.sh                # ← Script de arranque
    └── backoffice/             # ← Código React/TypeScript
```

---

## ✅ Verificación Post-Instalación

```bash
# 1. Backend responde
curl http://localhost:8000/health
# Esperado: {"status":"healthy"}

# 2. Frontend carga
curl -I http://localhost:3001
# Esperado: HTTP/1.1 200 OK

# 3. Logs sin errores
docker compose logs --tail=50

# 4. Health checks OK
docker compose ps
# Esperado: ambos servicios en "Up" con "(healthy)"
```

---

## 🚀 Siguiente Paso

Todo funcionando? **Lee la documentación completa**: [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md)

---

**Dockerización por**: Claude Sonnet 4.5  
**Fecha**: 28 octubre 2026
