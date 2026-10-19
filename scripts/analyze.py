#!/usr/bin/env python3
"""
Analizador de Incidencias Postventa - Brasaland
Script CLI para validar y analizar incidencias desde CSV

Uso: python analyze.py incidents-BRASALAND.csv [--export]
"""

import sys
import csv
import argparse
from datetime import datetime
from typing import Dict, List, Tuple
from collections import Counter


# ============ VALORES PERMITIDOS SEGÚN BRIEFING ============

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


# ============ FUNCIONES DE VALIDACIÓN ============

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


# ============ ANÁLISIS DE DATOS ============

def analizar_incidencias(archivo_csv: str) -> Dict:
    """
    Analiza el archivo CSV y retorna métricas.
    """
    registros_validos = []
    registros_invalidos = []

    try:
        with open(archivo_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for i, registro in enumerate(reader, start=2):  # Start at 2 (header is line 1)
                es_valido, razon = validar_registro(registro)

                if es_valido:
                    registros_validos.append(registro)
                else:
                    registros_invalidos.append({
                        'linea': i,
                        'id': registro.get('id_incidencia', 'N/A'),
                        'razon': razon
                    })

    except FileNotFoundError:
        print(f"❌ Error: Archivo '{archivo_csv}' no encontrado")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error al leer archivo: {e}")
        sys.exit(1)

    # Calcular métricas solo sobre registros válidos
    metricas = {
        'total_procesados': len(registros_validos) + len(registros_invalidos),
        'total_validos': len(registros_validos),
        'total_invalidos': len(registros_invalidos),
        'registros_invalidos': registros_invalidos,
        'por_categoria': Counter(r['categoria'] for r in registros_validos),
        'por_estado': Counter(r['estado'] for r in registros_validos),
        'por_pais': Counter(r['pais'] for r in registros_validos),
        'satisfaccion_promedio': calcular_satisfaccion_promedio(registros_validos),
        'registros_validos': registros_validos  # Para exportar
    }

    return metricas


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


# ============ VISUALIZACIÓN DE RESULTADOS ============

def imprimir_resultados(metricas: Dict):
    """Imprime resultados en consola con formato limpio"""
    print("\n" + "=" * 70)
    print("  ANÁLISIS DE INCIDENCIAS POSTVENTA - BRASALAND")
    print("=" * 70)

    # Resumen General
    print("\n📊 RESUMEN GENERAL")
    print("-" * 70)
    print(f"  Total de registros procesados: {metricas['total_procesados']}")
    print(f"  ✅ Registros válidos:           {metricas['total_validos']}")
    print(f"  ❌ Registros inválidos:         {metricas['total_invalidos']}")

    # Registros Inválidos (si los hay)
    if metricas['total_invalidos'] > 0:
        print("\n❌ REGISTROS INVÁLIDOS DETECTADOS")
        print("-" * 70)
        for inv in metricas['registros_invalidos']:
            print(f"  Línea {inv['linea']} | ID: {inv['id']} | {inv['razon']}")

    # Solo si hay registros válidos, mostrar métricas
    if metricas['total_validos'] > 0:
        # Por Categoría
        print("\n📂 INCIDENCIAS POR CATEGORÍA")
        print("-" * 70)
        for categoria, cantidad in sorted(metricas['por_categoria'].items()):
            porcentaje = (cantidad / metricas['total_validos']) * 100
            print(f"  {categoria:20} {cantidad:5} ({porcentaje:5.1f}%)")

        # Por Estado
        print("\n🔄 INCIDENCIAS POR ESTADO")
        print("-" * 70)
        for estado, cantidad in sorted(metricas['por_estado'].items()):
            porcentaje = (cantidad / metricas['total_validos']) * 100
            print(f"  {estado:20} {cantidad:5} ({porcentaje:5.1f}%)")

        # Por País
        print("\n🌎 INCIDENCIAS POR PAÍS")
        print("-" * 70)
        for pais, cantidad in sorted(metricas['por_pais'].items()):
            pais_nombre = "Colombia" if pais == "CO" else "Florida, USA"
            porcentaje = (cantidad / metricas['total_validos']) * 100
            print(f"  {pais_nombre:20} {cantidad:5} ({porcentaje:5.1f}%)")

        # Satisfacción
        if metricas['satisfaccion_promedio'] > 0:
            print("\n⭐ ÍNDICE DE SATISFACCIÓN")
            print("-" * 70)
            print(f"  Promedio (casos cerrados): {metricas['satisfaccion_promedio']:.2f} / 5.00")

            # Interpretación
            if metricas['satisfaccion_promedio'] >= 4.0:
                interpretacion = "🟢 EXCELENTE"
            elif metricas['satisfaccion_promedio'] >= 3.0:
                interpretacion = "🟡 BUENO"
            else:
                interpretacion = "🔴 REQUIERE ATENCIÓN"
            print(f"  Evaluación:                {interpretacion}")
    else:
        print("\n⚠️  No hay registros válidos para analizar")

    print("\n" + "=" * 70)


def exportar_resultados(metricas: Dict):
    """Exporta resultados a results.csv"""
    try:
        with open('results.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(['Métrica', 'Valor'])

            # Resumen General
            writer.writerow(['Total Procesados', metricas['total_procesados']])
            writer.writerow(['Total Válidos', metricas['total_validos']])
            writer.writerow(['Total Inválidos', metricas['total_invalidos']])
            writer.writerow([])

            # Por Categoría
            writer.writerow(['CATEGORÍA', 'CANTIDAD'])
            for categoria, cantidad in sorted(metricas['por_categoria'].items()):
                writer.writerow([categoria, cantidad])
            writer.writerow([])

            # Por Estado
            writer.writerow(['ESTADO', 'CANTIDAD'])
            for estado, cantidad in sorted(metricas['por_estado'].items()):
                writer.writerow([estado, cantidad])
            writer.writerow([])

            # Por País
            writer.writerow(['PAÍS', 'CANTIDAD'])
            for pais, cantidad in sorted(metricas['por_pais'].items()):
                pais_nombre = "Colombia" if pais == "CO" else "Florida, USA"
                writer.writerow([pais_nombre, cantidad])
            writer.writerow([])

            # Satisfacción
            writer.writerow(['SATISFACCIÓN PROMEDIO', f"{metricas['satisfaccion_promedio']:.2f}"])

        print(f"\n✅ Resultados exportados a: results.csv")

    except Exception as e:
        print(f"\n❌ Error al exportar resultados: {e}")


# ============ MAIN ============

def main():
    """Punto de entrada del script"""
    # Parser de argumentos
    parser = argparse.ArgumentParser(
        description='Analizador de Incidencias Postventa - Brasaland',
        epilog='Ejemplo: python analyze.py incidents.csv --export'
    )
    parser.add_argument('archivo_csv', help='Archivo CSV con incidencias')
    parser.add_argument('--export', action='store_true', help='Exportar resultados a results.csv')

    args = parser.parse_args()

    # Analizar incidencias
    print("\n🔍 Analizando incidencias...")
    metricas = analizar_incidencias(args.archivo_csv)

    # Mostrar resultados
    imprimir_resultados(metricas)

    # Exportar si se solicitó
    if args.export and metricas['total_validos'] > 0:
        exportar_resultados(metricas)

    print("\n✅ Análisis completado\n")


if __name__ == "__main__":
    main()
