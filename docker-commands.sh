#!/bin/bash
# ============================================
# Brasaland Docker - Comandos Útiles
# Atajos para operaciones comunes de Docker
# ============================================

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para imprimir headers
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Función para mensajes de éxito
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Función para mensajes de error
error() {
    echo -e "${RED}❌ $1${NC}"
}

# Función para mensajes de info
info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# ============================================
# COMANDOS PRINCIPALES
# ============================================

# Levantar todo
up() {
    print_header "🚀 Levantando Brasaland Platform"
    docker compose up --build
}

# Levantar en background
up_d() {
    print_header "🚀 Levantando en Background"
    docker compose up -d --build
    success "Servicios levantados"
    docker compose ps
}

# Parar todo
down() {
    print_header "🛑 Deteniendo Servicios"
    docker compose down
    success "Servicios detenidos"
}

# Reiniciar todo
restart() {
    print_header "🔄 Reiniciando Servicios"
    docker compose restart
    success "Servicios reiniciados"
}

# Ver logs en tiempo real
logs() {
    print_header "📋 Logs en Tiempo Real"
    docker compose logs -f
}

# Ver logs de backend
logs_backend() {
    print_header "📋 Logs Backend (FastAPI)"
    docker compose logs -f backend
}

# Ver logs de frontend
logs_frontend() {
    print_header "📋 Logs Frontend (Next.js)"
    docker compose logs -f frontend
}

# Ver estado de servicios
status() {
    print_header "📊 Estado de Servicios"
    docker compose ps
    echo ""
    info "Health Checks:"
    docker compose ps --format json | jq -r '.[] | "\(.Service): \(.Health)"'
}

# Reconstruir imágenes
rebuild() {
    print_header "🔨 Reconstruyendo Imágenes"
    docker compose build --no-cache
    success "Imágenes reconstruidas"
}

# Limpiar todo (⚠️ incluye volúmenes)
clean() {
    print_header "🧹 Limpieza Completa"
    error "⚠️  ADVERTENCIA: Esto eliminará todos los volúmenes (datos de TinyDB)"
    read -p "¿Continuar? (y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        docker compose down -v --remove-orphans
        docker image prune -f
        success "Limpieza completada"
    else
        info "Limpieza cancelada"
    fi
}

# ============================================
# COMANDOS DE DESARROLLO
# ============================================

# Shell en backend
shell_backend() {
    print_header "🐚 Shell Backend"
    docker compose exec backend bash
}

# Shell en frontend
shell_frontend() {
    print_header "🐚 Shell Frontend"
    docker compose exec frontend sh
}

# Verificar conectividad interna
test_network() {
    print_header "🔗 Test Conectividad Interna"
    info "Probando frontend → backend..."
    docker compose exec frontend curl -s http://backend:8000/health
    success "Conectividad OK"
}

# Ver variables de entorno del backend
env_backend() {
    print_header "🔐 Variables Backend"
    docker compose exec backend env | grep -E "SECRET|SUPABASE|API_" | sort
}

# Ver variables de entorno del frontend
env_frontend() {
    print_header "🔐 Variables Frontend"
    docker compose exec frontend env | grep NEXT_PUBLIC | sort
}

# Seed incidencias de prueba
seed_incidents() {
    print_header "🌱 Seeding Incidencias"
    docker compose exec backend python scripts/seed_incidents.py /app/scripts/test-incidents.csv
}

# Ver uso de recursos
stats() {
    print_header "💻 Uso de Recursos"
    docker stats --no-stream
}

# Verificar health checks
health() {
    print_header "🏥 Health Checks"

    echo -e "${YELLOW}Backend:${NC}"
    curl -s http://localhost:8000/health | jq '.'

    echo ""
    echo -e "${YELLOW}Frontend:${NC}"
    curl -s -I http://localhost:3001 | head -n 1
}

# ============================================
# COMANDOS DE TROUBLESHOOTING
# ============================================

# Ver qué usa los puertos
ports() {
    print_header "🔌 Puertos en Uso"
    echo -e "${YELLOW}Puerto 8000 (Backend):${NC}"
    lsof -i :8000 || echo "Libre"
    echo ""
    echo -e "${YELLOW}Puerto 3001 (Frontend):${NC}"
    lsof -i :3001 || echo "Libre"
}

# Recrear contenedores (sin reconstruir imágenes)
recreate() {
    print_header "♻️  Recreando Contenedores"
    docker compose up -d --force-recreate
    success "Contenedores recreados"
}

# Ver disco usado
disk() {
    print_header "💾 Uso de Disco Docker"
    docker system df -v
}

# Ver red Docker
network() {
    print_header "🌐 Red Docker"
    docker network inspect brasaland-network | jq '.[0] | {Name, Driver, Containers}'
}

# ============================================
# MENU DE AYUDA
# ============================================

help() {
    print_header "🐳 Brasaland Docker - Comandos Disponibles"

    echo -e "${GREEN}📦 COMANDOS PRINCIPALES${NC}"
    echo "  up              - Levantar servicios (foreground)"
    echo "  up_d            - Levantar servicios (background)"
    echo "  down            - Detener servicios"
    echo "  restart         - Reiniciar servicios"
    echo "  status          - Ver estado de servicios"
    echo "  rebuild         - Reconstruir imágenes sin caché"
    echo "  clean           - Limpiar todo (⚠️ borra volúmenes)"
    echo ""

    echo -e "${GREEN}📋 LOGS${NC}"
    echo "  logs            - Ver logs de todos los servicios"
    echo "  logs_backend    - Ver logs solo del backend"
    echo "  logs_frontend   - Ver logs solo del frontend"
    echo ""

    echo -e "${GREEN}🛠️  DESARROLLO${NC}"
    echo "  shell_backend   - Abrir shell en contenedor backend"
    echo "  shell_frontend  - Abrir shell en contenedor frontend"
    echo "  test_network    - Test conectividad interna"
    echo "  env_backend     - Ver variables de entorno backend"
    echo "  env_frontend    - Ver variables de entorno frontend"
    echo "  seed_incidents  - Seed datos de prueba"
    echo "  stats           - Ver uso de recursos"
    echo "  health          - Verificar health checks"
    echo ""

    echo -e "${GREEN}🐛 TROUBLESHOOTING${NC}"
    echo "  ports           - Ver qué usa puertos 8000/3001"
    echo "  recreate        - Recrear contenedores"
    echo "  disk            - Ver uso de disco Docker"
    echo "  network         - Inspeccionar red Docker"
    echo ""

    echo -e "${YELLOW}Uso: source docker-commands.sh && <comando>${NC}"
    echo -e "${YELLOW}Ejemplo: source docker-commands.sh && up_d${NC}"
}

# Si se ejecuta directamente, mostrar ayuda
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    help
fi
