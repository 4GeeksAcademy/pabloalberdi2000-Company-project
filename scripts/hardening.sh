#!/bin/bash
###############################################################################
# Server Hardening Script - Brasaland Digital
#
# PROPÓSITO: Bastionado del servidor siguiendo principios de mínimo privilegio
# CUMPLIMIENTO: OWASP, CIS Benchmarks, NIST
#
# EJECUCIÓN: sudo ./scripts/hardening.sh
#
# ⚠️  ADVERTENCIA: Este script realiza cambios críticos en la configuración
#    del sistema. Revisar y ajustar según entorno antes de ejecutar.
###############################################################################

set -euo pipefail  # Modo estricto: error en fallo, variables no definidas, pipes

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funciones de utilidad
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
       log_error "Este script debe ejecutarse como root (sudo)"
       exit 1
    fi
}

###############################################################################
# 1. CREACIÓN DE USUARIO OPERATIVO (Principio de Mínimo Privilegio)
###############################################################################

create_app_user() {
    log_info "=== 1. Creación de Usuario Operativo ==="

    APP_USER="brasaland"
    APP_GROUP="brasaland"
    APP_HOME="/opt/brasaland"

    # Verificar si el usuario ya existe
    if id "$APP_USER" &>/dev/null; then
        log_warn "Usuario $APP_USER ya existe, omitiendo creación"
    else
        log_info "Creando usuario $APP_USER..."

        # Crear grupo
        groupadd -r "$APP_GROUP" 2>/dev/null || true

        # Crear usuario sin shell interactivo (seguridad)
        useradd -r -g "$APP_GROUP" -d "$APP_HOME" -s /bin/bash -c "Brasaland App User" "$APP_USER"

        log_info "Usuario $APP_USER creado exitosamente"
    fi

    # Crear directorio home si no existe
    if [[ ! -d "$APP_HOME" ]]; then
        mkdir -p "$APP_HOME"
        chown "$APP_USER:$APP_GROUP" "$APP_HOME"
        chmod 750 "$APP_HOME"
    fi

    # Configurar sudoers (permisos acotados)
    SUDOERS_FILE="/etc/sudoers.d/brasaland"

    if [[ ! -f "$SUDOERS_FILE" ]]; then
        log_info "Configurando sudoers para $APP_USER..."

        cat > "$SUDOERS_FILE" <<EOF
# Brasaland App User - Permisos sudo acotados
# Solo puede reiniciar servicios de la aplicación
$APP_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart brasaland-backend
$APP_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart brasaland-frontend
$APP_USER ALL=(ALL) NOPASSWD: /bin/systemctl status brasaland-*
$APP_USER ALL=(ALL) NOPASSWD: /bin/journalctl -u brasaland-*
EOF

        # Validar sintaxis sudoers
        visudo -c -f "$SUDOERS_FILE"
        chmod 0440 "$SUDOERS_FILE"

        log_info "Sudoers configurado"
    fi
}

###############################################################################
# 2. CONFIGURACIÓN SSH ENDURECIDA
###############################################################################

harden_ssh() {
    log_info "=== 2. Endurecimiento SSH ==="

    SSHD_CONFIG="/etc/ssh/sshd_config"
    SSHD_BACKUP="/etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)"

    # Backup de configuración original
    log_info "Creando backup de $SSHD_CONFIG..."
    cp "$SSHD_CONFIG" "$SSHD_BACKUP"

    # Aplicar configuraciones de seguridad
    log_info "Aplicando configuraciones SSH endurecidas..."

    # Deshabilitar login como root
    sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' "$SSHD_CONFIG"

    # Deshabilitar autenticación por contraseña (solo SSH keys)
    sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' "$SSHD_CONFIG"

    # Deshabilitar autenticación vacía
    sed -i 's/^#*PermitEmptyPasswords.*/PermitEmptyPasswords no/' "$SSHD_CONFIG"

    # Limitar intentos de autenticación
    sed -i 's/^#*MaxAuthTries.*/MaxAuthTries 3/' "$SSHD_CONFIG"

    # Limitar sesiones concurrentes
    sed -i 's/^#*MaxSessions.*/MaxSessions 5/' "$SSHD_CONFIG"

    # Deshabilitar X11 Forwarding (no necesario)
    sed -i 's/^#*X11Forwarding.*/X11Forwarding no/' "$SSHD_CONFIG"

    # Usar protocolo SSH 2 únicamente
    if ! grep -q "^Protocol 2" "$SSHD_CONFIG"; then
        echo "Protocol 2" >> "$SSHD_CONFIG"
    fi

    # Configurar timeout de sesión inactiva
    if ! grep -q "^ClientAliveInterval" "$SSHD_CONFIG"; then
        echo "ClientAliveInterval 300" >> "$SSHD_CONFIG"
        echo "ClientAliveCountMax 2" >> "$SSHD_CONFIG"
    fi

    # Validar configuración SSH
    log_info "Validando configuración SSH..."
    sshd -t

    if [[ $? -eq 0 ]]; then
        log_info "Configuración SSH válida"
        log_warn "Reiniciando servicio SSH..."
        systemctl reload sshd
        log_info "SSH endurecido exitosamente"
    else
        log_error "Error en configuración SSH, restaurando backup..."
        cp "$SSHD_BACKUP" "$SSHD_CONFIG"
        exit 1
    fi
}

###############################################################################
# 3. PERMISOS DEL SISTEMA DE ARCHIVOS
###############################################################################

set_file_permissions() {
    log_info "=== 3. Configuración de Permisos del Sistema de Archivos ==="

    APP_USER="brasaland"
    APP_GROUP="brasaland"
    PROJECT_ROOT="/opt/brasaland"

    log_warn "AJUSTAR PROJECT_ROOT según la ubicación real de la aplicación"

    # Crear estructura de directorios
    log_info "Creando estructura de directorios..."
    mkdir -p "$PROJECT_ROOT"/{services,uis,data,logs,config}

    # Permisos de código fuente (solo lectura para proceso web)
    log_info "Configurando permisos de código fuente..."
    chown -R "$APP_USER:$APP_GROUP" "$PROJECT_ROOT"/services
    chown -R "$APP_USER:$APP_GROUP" "$PROJECT_ROOT"/uis
    chmod -R 750 "$PROJECT_ROOT"/services
    chmod -R 750 "$PROJECT_ROOT"/uis

    # Permisos de directorio de datos (lectura/escritura)
    log_info "Configurando permisos de datos..."
    chown -R "$APP_USER:$APP_GROUP" "$PROJECT_ROOT"/data
    chmod -R 770 "$PROJECT_ROOT"/data

    # Permisos de logs (escritura exclusiva)
    log_info "Configurando permisos de logs..."
    chown -R "$APP_USER:$APP_GROUP" "$PROJECT_ROOT"/logs
    chmod 700 "$PROJECT_ROOT"/logs

    # Permisos de archivos de configuración sensibles (.env)
    log_info "Configurando permisos de archivos .env..."
    find "$PROJECT_ROOT" -name ".env*" -type f -exec chown "$APP_USER:$APP_GROUP" {} \;
    find "$PROJECT_ROOT" -name ".env*" -type f -exec chmod 600 {} \;

    # Permisos de certificados SSL
    if [[ -d "$PROJECT_ROOT/config/ssl" ]]; then
        log_info "Configurando permisos de certificados SSL..."
        chown -R root:$APP_GROUP "$PROJECT_ROOT"/config/ssl
        chmod 640 "$PROJECT_ROOT"/config/ssl/*.pem 2>/dev/null || true
        chmod 640 "$PROJECT_ROOT"/config/ssl/*.key 2>/dev/null || true
    fi

    log_info "Permisos de sistema de archivos configurados"
}

###############################################################################
# 4. FIREWALL CON UFW (Uncomplicated Firewall)
###############################################################################

configure_firewall() {
    log_info "=== 4. Configuración de Firewall (UFW) ==="

    # Verificar si ufw está instalado
    if ! command -v ufw &> /dev/null; then
        log_warn "UFW no está instalado, instalando..."
        apt-get update -qq
        apt-get install -y ufw
    fi

    log_info "Configurando reglas de firewall..."

    # Política por defecto: denegar entrante, permitir saliente
    ufw default deny incoming
    ufw default allow outgoing

    # Permitir SSH (puerto personalizado si se configuró)
    SSH_PORT=$(grep -E "^Port " /etc/ssh/sshd_config | awk '{print $2}' || echo "22")
    log_info "Permitiendo SSH en puerto $SSH_PORT..."
    ufw allow "$SSH_PORT"/tcp comment 'SSH'

    # Permitir HTTP (80)
    log_info "Permitiendo HTTP (80)..."
    ufw allow 80/tcp comment 'HTTP'

    # Permitir HTTPS (443)
    log_info "Permitiendo HTTPS (443)..."
    ufw allow 443/tcp comment 'HTTPS'

    # Limitar conexiones SSH (rate limiting contra brute force)
    log_info "Configurando rate limiting para SSH..."
    ufw limit "$SSH_PORT"/tcp comment 'SSH rate limit'

    # Habilitar firewall
    log_warn "Habilitando firewall UFW..."
    echo "y" | ufw enable

    # Mostrar estado
    log_info "Estado del firewall:"
    ufw status verbose

    log_info "Firewall configurado exitosamente"
}

###############################################################################
# 5. CONFIGURACIONES ADICIONALES DE SEGURIDAD
###############################################################################

additional_hardening() {
    log_info "=== 5. Configuraciones Adicionales de Seguridad ==="

    # Deshabilitar IPv6 (si no se usa)
    log_info "Deshabilitando IPv6..."
    cat >> /etc/sysctl.conf <<EOF

# Deshabilitar IPv6 (Brasaland Hardening)
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
EOF

    # Protección contra SYN flood
    log_info "Configurando protección contra SYN flood..."
    cat >> /etc/sysctl.conf <<EOF

# Protección contra SYN flood
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_syn_retries = 5
EOF

    # Deshabilitar ICMP redirects
    cat >> /etc/sysctl.conf <<EOF

# Deshabilitar ICMP redirects
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
EOF

    # Protección contra IP spoofing
    cat >> /etc/sysctl.conf <<EOF

# Protección contra IP spoofing
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
EOF

    # Aplicar cambios sysctl
    sysctl -p

    # Configurar límites de recursos (ulimits)
    log_info "Configurando límites de recursos..."
    cat > /etc/security/limits.d/brasaland.conf <<EOF
# Brasaland - Límites de recursos
brasaland soft nofile 4096
brasaland hard nofile 8192
brasaland soft nproc 2048
brasaland hard nproc 4096
EOF

    # Fail2ban para protección contra brute force
    if command -v fail2ban-client &> /dev/null; then
        log_info "Fail2ban ya está instalado"
    else
        log_warn "Fail2ban no está instalado. Recomendado: apt-get install fail2ban"
    fi

    log_info "Configuraciones adicionales aplicadas"
}

###############################################################################
# 6. AUDITORÍA Y VERIFICACIÓN
###############################################################################

audit_hardening() {
    log_info "=== 6. Auditoría de Configuración ==="

    # Verificar usuario creado
    if id "brasaland" &>/dev/null; then
        log_info "✓ Usuario brasaland existe"
    else
        log_error "✗ Usuario brasaland NO existe"
    fi

    # Verificar SSH
    if grep -q "^PermitRootLogin no" /etc/ssh/sshd_config; then
        log_info "✓ SSH: PermitRootLogin no"
    else
        log_warn "✗ SSH: PermitRootLogin no configurado"
    fi

    if grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config; then
        log_info "✓ SSH: PasswordAuthentication no"
    else
        log_warn "✗ SSH: PasswordAuthentication no configurado"
    fi

    # Verificar firewall
    if ufw status | grep -q "Status: active"; then
        log_info "✓ Firewall UFW activo"
    else
        log_warn "✗ Firewall UFW inactivo"
    fi

    # Verificar permisos .env
    ENV_FILES=$(find /opt/brasaland -name ".env*" -type f 2>/dev/null)
    if [[ -n "$ENV_FILES" ]]; then
        for env_file in $ENV_FILES; do
            PERMS=$(stat -c %a "$env_file")
            if [[ "$PERMS" == "600" ]]; then
                log_info "✓ $env_file: permisos 600"
            else
                log_warn "✗ $env_file: permisos $PERMS (debería ser 600)"
            fi
        done
    fi

    log_info "Auditoría completada"
}

###############################################################################
# MAIN
###############################################################################

main() {
    log_info "========================================="
    log_info "  Brasaland Digital - Server Hardening"
    log_info "========================================="
    log_info ""

    check_root

    log_warn "Este script realizará cambios críticos en el sistema"
    log_warn "Asegúrate de tener una copia de seguridad antes de continuar"
    read -p "¿Deseas continuar? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Operación cancelada por el usuario"
        exit 0
    fi

    create_app_user
    harden_ssh
    set_file_permissions
    configure_firewall
    additional_hardening
    audit_hardening

    log_info ""
    log_info "========================================="
    log_info "  ✓ Hardening Completado Exitosamente"
    log_info "========================================="
    log_info ""
    log_warn "IMPORTANTE: Cerrar sesión SSH actual y reconectar"
    log_warn "  con el usuario 'brasaland' usando SSH keys"
    log_info ""
}

main "$@"
