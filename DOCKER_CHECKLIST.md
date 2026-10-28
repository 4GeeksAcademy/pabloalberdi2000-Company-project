# ✅ Docker Setup Checklist - Brasaland

Usa esta lista para verificar que tu entorno Docker está correctamente configurado.

---

## 📋 PRE-REQUISITOS

- [ ] Docker instalado (`docker --version` muestra ≥ 20.10)
- [ ] Docker Compose instalado (`docker compose version` muestra ≥ 2.0)
- [ ] Git instalado
- [ ] Repositorio clonado

---

## 🔧 CONFIGURACIÓN INICIAL

- [ ] Archivo `.env` creado desde `.env.example`
- [ ] `SECRET_KEY` configurado (mínimo 32 caracteres)
- [ ] `RESET_TOKEN_SECRET_KEY` configurado (diferente al anterior)
- [ ] `SUPABASE_DATABASE_URL` configurado (si usas inventario)
- [ ] Archivo `uis/start.sh` tiene permisos de ejecución

**Verificar permisos**:
```bash
ls -la uis/start.sh
# Debe mostrar: -rwxr-xr-x
```

---

## 🚀 PRIMER ARRANQUE

- [ ] Ejecutar `docker compose up --build`
- [ ] Backend levanta sin errores
- [ ] Frontend levanta sin errores
- [ ] Ambos servicios marcan como "healthy"

**Verificar**:
```bash
docker compose ps
# Ambos deben mostrar "(healthy)"
```

---

## 🏥 HEALTH CHECKS

- [ ] Backend responde en http://localhost:8000/health
- [ ] Frontend responde en http://localhost:3001
- [ ] API Docs accesible en http://localhost:8000/docs

**Verificar Backend**:
```bash
curl http://localhost:8000/health
# Esperado: {"status":"healthy"}
```

**Verificar Frontend**:
```bash
curl -I http://localhost:3001
# Esperado: HTTP/1.1 200 OK
```

---

## 🔗 CONECTIVIDAD INTERNA

- [ ] Frontend puede alcanzar backend

**Verificar**:
```bash
docker compose exec frontend curl http://backend:8000/health
# Esperado: {"status":"healthy"}
```

---

## 💾 PERSISTENCIA

- [ ] Volumen `backend-data` creado
- [ ] TinyDB persiste entre reinicios

**Verificar volumen**:
```bash
docker volume ls | grep backend-data
# Debe mostrar: brasaland-backend-data
```

---

## 🔄 HOT RELOAD

- [ ] Cambios en Python (.py) recargan backend automáticamente
- [ ] Cambios en TypeScript (.tsx) recargan frontend automáticamente

**Probar Backend**:
1. Editar `services/api/app/main.py`
2. Agregar print("TEST") en cualquier endpoint
3. Ver logs: `docker compose logs -f backend`
4. Debe mostrar "Reloading..."

**Probar Frontend**:
1. Editar `uis/backoffice/app/page.tsx`
2. Cambiar cualquier texto
3. Refrescar navegador en http://localhost:3001
4. Cambio debe verse inmediatamente

---

## 📋 LOGS

- [ ] Logs de backend visibles
- [ ] Logs de frontend visibles
- [ ] Sin errores críticos en logs

**Ver logs**:
```bash
docker compose logs -f
```

---

## 🛠️ COMANDOS ÚTILES

- [ ] `make help` funciona (si tienes make)
- [ ] Script `docker-commands.sh` es ejecutable

**Probar Make**:
```bash
make help
# Debe mostrar lista de comandos
```

**Probar script**:
```bash
source docker-commands.sh
help
# Debe mostrar lista de funciones
```

---

## 🐛 TROUBLESHOOTING

Si algo falla, revisar:

**Puerto 8000 ocupado**:
```bash
lsof -i :8000
# Matar proceso: kill -9 <PID>
```

**Puerto 3001 ocupado**:
```bash
lsof -i :3001
# Matar proceso: kill -9 <PID>
```

**Backend no levanta**:
```bash
docker compose logs backend
# Revisar errores en output
```

**Frontend no levanta**:
```bash
docker compose logs frontend
# Revisar errores en output
```

**Rebuild desde cero**:
```bash
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

---

## ✅ VERIFICACIÓN FINAL

Todas las siguientes URLs deben responder:

- [ ] http://localhost:8000 → API FastAPI
- [ ] http://localhost:8000/docs → Swagger UI
- [ ] http://localhost:8000/health → `{"status":"healthy"}`
- [ ] http://localhost:3001 → Backoffice Next.js

**Si todas responden**: ✅ **Setup completo exitoso**

---

## 📚 SIGUIENTE PASO

Setup completo? Lee la documentación:

- **Quick Start**: [DOCKER_QUICKSTART.md](./DOCKER_QUICKSTART.md)
- **Guía Completa**: [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md)
- **Resumen**: [DOCKER_SUMMARY.md](./DOCKER_SUMMARY.md)

---

**Checklist creado**: 28 octubre 2026  
**Versión**: 1.0
