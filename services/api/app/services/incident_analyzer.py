"""
Servicio de análisis de incidencias
Reutiliza la lógica de validación del paquete compartido
"""
import csv
from io import StringIO
from typing import List
from collections import Counter

from app.schemas.incident import (
    IncidentInvalido,
    MetricasPorCategoria,
    MetricasPorEstado,
    MetricasPorPais,
    AnalysisResponse
)

# Importar validaciones desde paquete compartido transversal
from brasaland_shared import (
    validar_registro,
    calcular_satisfaccion_promedio,
    obtener_evaluacion_satisfaccion
)


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
