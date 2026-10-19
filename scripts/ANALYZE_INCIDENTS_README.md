# Script de Análisis de Incidencias Postventa - Brasaland

## Descripción

Script CLI en Python para validar y analizar incidencias postventa de los 14 locales de Brasaland (Colombia y Florida).

## Requisitos

- Python 3.7+
- No requiere dependencias externas (solo bibliotecas estándar)

## Uso

### Análisis Básico

```bash
python scripts/analyze.py archivo.csv
```

Muestra en consola:
- Total de registros procesados
- Registros válidos e inválidos (con detalles de errores)
- Incidencias por categoría
- Incidencias por estado
- Incidencias por país
- Índice de satisfacción promedio

### Exportar Resultados a CSV

```bash
python scripts/analyze.py archivo.csv --export
```

Genera un archivo `results.csv` en el directorio actual con todas las métricas.

### Ver Ayuda

```bash
python scripts/analyze.py --help
```

## Formato del CSV de Entrada

Ver especificaciones completas en [`docs/BRIEFING_INCIDENCIAS.md`](../docs/BRIEFING_INCIDENCIAS.md)

### Campos Obligatorios

| Campo | Tipo | Ejemplo |
|-------|------|---------|
| `id_incidencia` | string | INC001 |
| `fecha` | date (YYYY-MM-DD) | 2026-10-15 |
| `categoria` | string | calidad_comida |
| `descripcion` | string | Carne poco cocida |
| `estado` | string | cerrado |
| `local` | string | medellin_centro |
| `pais` | string | CO |

### Campos Opcionales

- `satisfaccion` (integer 1-5, **obligatorio si estado es "cerrado"**)
- `email_cliente` (string, no analizado - PII)
- `telefono` (string, no analizado - PII)

## Categorías Permitidas

- `calidad_comida` - Problemas con sabor, cocción, temperatura, presentación
- `servicio_cliente` - Atención del personal, tiempos de espera, trato
- `operaciones` - Problemas logísticos, stock, proveedores
- `infraestructura` - Equipos, instalaciones, limpieza
- `pedidos_online` - Problemas con app o web
- `facturacion` - Errores en cuentas, cobros

## Estados Permitidos

- `abierto` - Incidencia reportada, pendiente de atención
- `en_proceso` - Se está trabajando en la solución
- `cerrado` - Incidencia resuelta
- `descartado` - Incidencia no procede o duplicada

## Locales Válidos

### Colombia (CO)
- medellin_centro, medellin_poblado, medellin_envigado
- bogota_zona_rosa, bogota_usaquen, bogota_suba
- cali_norte, cali_sur
- cartagena_centro, barranquilla_norte

### Florida (US)
- miami_beach, miami_downtown
- orlando_international, tampa_centro

## Ejemplo de Salida

```
======================================================================
  ANÁLISIS DE INCIDENCIAS POSTVENTA - BRASALAND
======================================================================

📊 RESUMEN GENERAL
----------------------------------------------------------------------
  Total de registros procesados: 10
  ✅ Registros válidos:           10
  ❌ Registros inválidos:         0

📂 INCIDENCIAS POR CATEGORÍA
----------------------------------------------------------------------
  calidad_comida           4 ( 40.0%)
  servicio_cliente         2 ( 20.0%)
  ...

⭐ ÍNDICE DE SATISFACCIÓN
----------------------------------------------------------------------
  Promedio (casos cerrados): 3.60 / 5.00
  Evaluación:                🟡 BUENO
```

## Validaciones

El script marca un registro como **inválido** si:

1. Falta algún campo obligatorio
2. La categoría no está en la lista permitida
3. El estado no está en la lista permitida
4. El país no es 'CO' o 'US'
5. El local no existe en la lista
6. El estado es "cerrado" pero falta el campo `satisfaccion`
7. El campo `satisfaccion` está fuera del rango 1-5
8. La fecha no tiene formato válido YYYY-MM-DD

## Archivo de Prueba

Se incluye `test-incidents.csv` con 10 registros de ejemplo para probar el script.

```bash
python scripts/analyze.py scripts/test-incidents.csv
```

## Índice de Satisfacción

- **🟢 EXCELENTE** (4.0 - 5.0)
- **🟡 BUENO** (3.0 - 3.9)
- **🔴 REQUIERE ATENCIÓN** (1.0 - 2.9)

Solo se calcula sobre casos en estado "cerrado" con puntuación válida.

---

**Responsable:** Nicolás Park (CTO - Brasaland Digital)  
**Fase:** 1 - CLI Script  
**Versión:** 1.0  
**Fecha:** Octubre 2026
