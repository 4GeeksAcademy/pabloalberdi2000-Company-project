"""
Servicio de análisis de incidencias
Reutiliza la lógica del script CLI
"""
import csv
from io import StringIO
from datetime import datetime
from typing import Dict, List, Tuple
from collections import Counter

from app.schemas.incident import (
    IncidentInvalido,
    MetricasPorCategoria,
    MetricasPorEstado,
    MetricasPorPais,
    AnalysisResponse
)


# Valores permitidos según BRIEFING
CATEGORIAS_PERMITIDAS = {
    'calidad_comida',
    'servicio_cliente',
    'operaciones',
    'infraestructura',
    'pedidos_online',
    'facturacion'
}

ESTADOS_PERMITIDOS = {
    'abierto',
    'en_proceso',
    'cerrado',
    'descartado'
}

PAISES_PERMITIDOS = {'CO', 'US'}

LOCALES_PERMITIDOS = {
    # Colombia
    'medellin_centro', 'medellin_poblado', 'medellin_envigado',
    'bogota_zona_rosa', 'bogota_usaquen', 'bogota_suba',
    'cali_norte', 'cali_sur',
    'cartagena_centro', 'barranquilla_norte',
    # Florida
    'miami_beach', 'miami_downtown',
    'orlando_international', 'tampa_centro'
}

CAMPOS_OBLIGATORIOS = [
    'id_incidencia',
    'fecha',
    'categoria',
    'descripcion',
    'estado',
    'local',
    'pais'
]


def validar_fecha(fecha_str: str) -> bool:
    """Valida formato de fecha YYYY-MM-DD"""
    try:
        datetime.strptime(fecha_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validar_satisfaccion(satisfaccion_str: str) -> bool:
    """Valida que satisfacción esté en rango 1-5"""
    try:
        valor = int(satisfaccion_str)
        return 1 <= valor <= 5
    except ValueError:
        return False


def validar_registro(registro: Dict[str, str]) -> Tuple[bool, str]:
    """
    Valida un registro según reglas del BRIEFING.
    Retorna (es_valido, razon_invalido)
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
    """Retorna evaluación cualitativa del promedio de satisfacción"""
    if promedio >= 4.0:
        return "EXCELENTE"
    elif promedio >= 3.0:
        return "BUENO"
    else:
        return "REQUIERE ATENCIÓN"


async def analizar_csv(contenido: str) -> AnalysisResponse:
    """
    Analiza el contenido de un CSV y retorna métricas.

    Args:
        contenido: String con el contenido del archivo CSV

    Returns:
        AnalysisResponse con todas las métricas
    """
    registros_validos = []
    registros_invalidos = []

    # Procesar CSV desde string
    reader = csv.DictReader(StringIO(contenido))

    for i, registro in enumerate(reader, start=2):  # Start at 2 (header is line 1)
        es_valido, razon = validar_registro(registro)

        if es_valido:
            registros_validos.append(registro)
        else:
            registros_invalidos.append(
                IncidentInvalido(
                    linea=i,
                    id_incidencia=registro.get('id_incidencia', 'N/A'),
                    razon=razon
                )
            )

    # Calcular métricas solo sobre registros válidos
    total_validos = len(registros_validos)

    # Por categoría
    contador_categorias = Counter(r['categoria'] for r in registros_validos)
    por_categoria = [
        MetricasPorCategoria(
            categoria=cat,
            cantidad=cant,
            porcentaje=(cant / total_validos * 100) if total_validos > 0 else 0
        )
        for cat, cant in sorted(contador_categorias.items())
    ]

    # Por estado
    contador_estados = Counter(r['estado'] for r in registros_validos)
    por_estado = [
        MetricasPorEstado(
            estado=est,
            cantidad=cant,
            porcentaje=(cant / total_validos * 100) if total_validos > 0 else 0
        )
        for est, cant in sorted(contador_estados.items())
    ]

    # Por país
    contador_paises = Counter(r['pais'] for r in registros_validos)
    por_pais = [
        MetricasPorPais(
            pais=pais,
            pais_nombre="Colombia" if pais == "CO" else "Florida, USA",
            cantidad=cant,
            porcentaje=(cant / total_validos * 100) if total_validos > 0 else 0
        )
        for pais, cant in sorted(contador_paises.items())
    ]

    # Satisfacción
    satisfaccion_promedio = calcular_satisfaccion_promedio(registros_validos)
    satisfaccion_evaluacion = obtener_evaluacion_satisfaccion(satisfaccion_promedio)

    return AnalysisResponse(
        total_procesados=len(registros_validos) + len(registros_invalidos),
        total_validos=total_validos,
        total_invalidos=len(registros_invalidos),
        registros_invalidos=registros_invalidos,
        por_categoria=por_categoria,
        por_estado=por_estado,
        por_pais=por_pais,
        satisfaccion_promedio=satisfaccion_promedio,
        satisfaccion_evaluacion=satisfaccion_evaluacion
    )
