# ============================================
# Brasaland Docker - Makefile
# Atajos para comandos Docker más comunes
# ============================================

.PHONY: help up down restart logs status clean rebuild shell-backend shell-frontend health

# Colores
GREEN  := \033[0;32m
BLUE   := \033[0;34m
YELLOW := \033[1;33m
RED    := \033[0;31m
NC     := \033[0m

help: ## Mostrar esta ayuda
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@echo "$(BLUE)🐳 Brasaland Docker - Makefile$(NC)"
	@echo "$(BLUE)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-18s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Uso: make <comando>$(NC)"
	@echo "$(YELLOW)Ejemplo: make up$(NC)"

# ============================================
# COMANDOS PRINCIPALES
# ============================================

up: ## Levantar servicios en background
	@echo "$(BLUE)🚀 Levantando servicios...$(NC)"
	docker compose up -d --build
	@echo "$(GREEN)✅ Servicios levantados$(NC)"
	@$(MAKE) status

up-logs: ## Levantar servicios con logs en foreground
	@echo "$(BLUE)🚀 Levantando servicios (logs visibles)...$(NC)"
	docker compose up --build

down: ## Detener servicios
	@echo "$(BLUE)🛑 Deteniendo servicios...$(NC)"
	docker compose down
	@echo "$(GREEN)✅ Servicios detenidos$(NC)"

restart: ## Reiniciar servicios
	@echo "$(BLUE)🔄 Reiniciando servicios...$(NC)"
	docker compose restart
	@echo "$(GREEN)✅ Servicios reiniciados$(NC)"

status: ## Ver estado de servicios
	@echo "$(BLUE)📊 Estado de servicios:$(NC)"
	@docker compose ps

logs: ## Ver logs en tiempo real (todos los servicios)
	docker compose logs -f

logs-backend: ## Ver logs del backend
	docker compose logs -f backend

logs-frontend: ## Ver logs del frontend
	docker compose logs -f frontend

# ============================================
# DESARROLLO
# ============================================

shell-backend: ## Abrir shell en backend
	docker compose exec backend bash

shell-frontend: ## Abrir shell en frontend
	docker compose exec frontend sh

health: ## Verificar health checks
	@echo "$(BLUE)🏥 Backend Health:$(NC)"
	@curl -s http://localhost:8000/health | jq '.' || echo "$(RED)❌ Backend no responde$(NC)"
	@echo ""
	@echo "$(BLUE)🏥 Frontend Health:$(NC)"
	@curl -s -I http://localhost:3001 | head -n 1 || echo "$(RED)❌ Frontend no responde$(NC)"

seed: ## Seed datos de prueba (incidencias)
	@echo "$(BLUE)🌱 Seeding incidencias...$(NC)"
	docker compose exec backend python scripts/seed_incidents.py /app/scripts/test-incidents.csv

# ============================================
# MANTENIMIENTO
# ============================================

rebuild: ## Reconstruir imágenes sin caché
	@echo "$(BLUE)🔨 Reconstruyendo imágenes...$(NC)"
	docker compose build --no-cache
	@echo "$(GREEN)✅ Imágenes reconstruidas$(NC)"

recreate: ## Recrear contenedores sin reconstruir
	@echo "$(BLUE)♻️  Recreando contenedores...$(NC)"
	docker compose up -d --force-recreate
	@echo "$(GREEN)✅ Contenedores recreados$(NC)"

clean: ## Limpiar todo (⚠️ borra volúmenes)
	@echo "$(RED)⚠️  ADVERTENCIA: Esto eliminará volúmenes (TinyDB)$(NC)"
	@read -p "Continuar? [y/N]: " confirm && [ "$$confirm" = "y" ]
	docker compose down -v --remove-orphans
	docker image prune -f
	@echo "$(GREEN)✅ Limpieza completada$(NC)"

prune: ## Limpiar imágenes no usadas (seguro)
	docker image prune -f
	@echo "$(GREEN)✅ Imágenes no usadas eliminadas$(NC)"

# ============================================
# TROUBLESHOOTING
# ============================================

ports: ## Ver qué usa los puertos 8000/3001
	@echo "$(BLUE)🔌 Puerto 8000 (Backend):$(NC)"
	@lsof -i :8000 || echo "Libre"
	@echo ""
	@echo "$(BLUE)🔌 Puerto 3001 (Frontend):$(NC)"
	@lsof -i :3001 || echo "Libre"

stats: ## Ver uso de recursos
	docker stats --no-stream

disk: ## Ver uso de disco Docker
	docker system df -v

network: ## Inspeccionar red Docker
	@docker network inspect brasaland-network | jq '.[0] | {Name, Driver, Containers}'

# ============================================
# PRODUCCIÓN
# ============================================

prod-up: ## Levantar en modo producción
	docker compose -f docker-compose.yml up -d --build
	@echo "$(GREEN)✅ Servicios en producción levantados$(NC)"

prod-logs: ## Ver logs de producción
	docker compose -f docker-compose.yml logs -f

prod-down: ## Detener producción
	docker compose -f docker-compose.yml down
	@echo "$(GREEN)✅ Servicios de producción detenidos$(NC)"

# ============================================
# VERIFICACIÓN
# ============================================

verify: health ## Verificación completa post-deploy
	@echo ""
	@echo "$(BLUE)🔍 Verificación completa:$(NC)"
	@echo ""
	@$(MAKE) status
	@echo ""
	@echo "$(YELLOW)💡 Si ambos servicios están 'healthy', todo está OK$(NC)"
