"""
Validadores de incidencias Brasaland

Lógica de validación reutilizable para:
- Script CLI de análisis (scripts/analyze.py)
- Script de seeding (scripts/seed_incidents.py)
- API backend (services/api)

Reglas según BRIEFING_INCIDENCIAS.md
"""
from datetime import datetime
from typing import Dict, List, Tuple

from .constants import (
    CATEGORIAS_PERMITIDAS,
    ESTADOS_PERMITIDOS,
    PAISES_PERMITIDOS,
    LOCALES_PERMITIDOS,
    CAMPOS_OBLIGATORIOS
)


def validar_fecha(fecha_str: str) -> bool:
    """
    Valida formato de fecha YYYY-MM-DD.

    Args:
        fecha_str: String con fecha a validar

    Returns:
        True si formato es válido, False en caso contrario
    """
    try:
        datetime.strptime(fecha_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validar_satisfaccion(satisfaccion_str: str) -> bool:
    """
    Valida que satisfacción esté en rango 1-5.

    Args:
        satisfaccion_str: String con puntuación a validar

    Returns:
        True si valor entre 1-5, False en caso contrario
    """
    try:
        valor = int(satisfaccion_str)
        return 1 <= valor <= 5
    except ValueError:
        return False


def validar_registro(registro: Dict[str, str]) -> Tuple[bool, str]:
    """
    Valida un registro de incidencia según reglas del BRIEFING.

    Reglas aplicadas:
    1. Campos obligatorios presentes y no vacíos
    2. Categoría en lista permitida
    3. Estado en lista permitida
    4. País en lista permitida (CO/US)
    5. Local en lista permitida (14 sedes)
    6. Fecha en formato YYYY-MM-DD
    7. Estado 'cerrado' requiere satisfacción (1-5)
    8. Satisfacción (si presente) debe ser válida

    Args:
        registro: Diccionario con campos del CSV

    Returns:
        Tupla (es_valido, razon_invalido)
        - es_valido: True si todas las reglas pasan
        - razon_invalido: String con razón del fallo (vacío si válido)
    """
    # 1. Verificar campos obligatorios
    for campo in CAMPOS_OBLIGATORIOS:
        if campo not in registro or not registro[campo].strip():
            return False, f"Campo obligatorio faltante: {campo}"

    # 2. Validar categoría
    if registro['categoria'] not in CATEGORIAS_PERMITIDAS:
        return False, f"Categoría inválida: {registro['categoria']}"

    # 3. Validar estado
    if registro['estado'] not in ESTADOS_PERMITIDOS:
        return False, f"Estado inválido: {registro['estado']}"

    # 4. Validar país
    if registro['pais'] not in PAISES_PERMITIDOS:
        return False, f"País inválido: {registro['pais']}"

    # 5. Validar local
    if registro['local'] not in LOCALES_PERMITIDOS:
        return False, f"Local inválido: {registro['local']}"

    # 6. Validar fecha
    if not validar_fecha(registro['fecha']):
        return False, f"Fecha inválida: {registro['fecha']}"

    # 7. Si estado es "cerrado", debe tener satisfacción válida
    if registro['estado'] == 'cerrado':
        satisfaccion = registro.get('satisfaccion', '').strip()
        if not satisfaccion:
            return False, "Estado 'cerrado' requiere campo 'satisfaccion'"
        if not validar_satisfaccion(satisfaccion):
            return False, f"Satisfacción fuera de rango (1-5): {satisfaccion}"

    # 8. Si hay satisfacción, debe ser válida
    if 'satisfaccion' in registro and registro['satisfaccion'].strip():
        if not validar_satisfaccion(registro['satisfaccion']):
            return False, f"Satisfacción inválida: {registro['satisfaccion']}"

    return True, ""


def calcular_satisfaccion_promedio(registros: List[Dict]) -> float:
    """
    Calcula el promedio de satisfacción para casos cerrados con puntuación válida.

    Args:
        registros: Lista de diccionarios con registros validados

    Returns:
        Promedio de satisfacción (0.0 si no hay casos cerrados con puntuación)
    """
    satisfacciones = []

    for registro in registros:
        if registro['estado'] == 'cerrado':
            satisfaccion_str = registro.get('satisfaccion', '').strip()
            if satisfaccion_str and validar_satisfaccion(satisfaccion_str):
                satisfacciones.append(int(satisfaccion_str))

    if satisfacciones:
        return sum(satisfacciones) / len(satisfacciones)
    return 0.0


def obtener_evaluacion_satisfaccion(promedio: float) -> str:
    """
    Retorna evaluación cualitativa del promedio de satisfacción.

    Escala:
    - >= 4.0: EXCELENTE
    - >= 3.0: BUENO
    - < 3.0: REQUIERE ATENCIÓN

    Args:
        promedio: Valor promedio de satisfacción (0-5)

    Returns:
        String con evaluación cualitativa
    """
    if promedio >= 4.0:
        return "EXCELENTE"
    elif promedio >= 3.0:
        return "BUENO"
    else:
        return "REQUIERE ATENCIÓN"
