#!/bin/bash
# Cron Job - Mantenimiento Diario de Memoria
#
# Este script debe ejecutarse diariamente (preferiblemente en horas de baja carga).
#
# Configuración de crontab:
#   # Ejecutar a las 2 AM todos los días
#   0 2 * * * /path/to/cron_memory_maintenance.sh >> /var/log/memory_maintenance.log 2>&1
#
# O para desarrollo local:
#   0 2 * * * cd /Users/alberdi/Desktop/4Geeks/pabloalberdi2000-Company-project && ./services/agent/cron_memory_maintenance.sh

set -e

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CLI_SCRIPT="$SCRIPT_DIR/memory_maintenance_cli.py"

# Timestamp
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "================================================================================"
echo "🔧 Mantenimiento Diario de Memoria - $TIMESTAMP"
echo "================================================================================"

# Cambiar a directorio del proyecto
cd "$PROJECT_ROOT"

# Verificar que el CLI existe
if [ ! -f "$CLI_SCRIPT" ]; then
    echo "❌ ERROR: CLI script no encontrado en $CLI_SCRIPT"
    exit 1
fi

# Ejecutar mantenimiento diario
echo ""
echo "📊 Ejecutando mantenimiento diario..."
echo ""

python3 "$CLI_SCRIPT" daily --json > "/tmp/memory_maintenance_$(date '+%Y%m%d').json"

# Verificar resultado
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Mantenimiento completado exitosamente"
    echo ""

    # Mostrar resumen
    python3 "$CLI_SCRIPT" health

    echo ""
    echo "📁 Resultado completo guardado en: /tmp/memory_maintenance_$(date '+%Y%m%d').json"
else
    echo ""
    echo "❌ Mantenimiento falló con código de error: $?"
    exit 1
fi

echo ""
echo "================================================================================"
echo "✅ Cron job completado - $TIMESTAMP"
echo "================================================================================"
