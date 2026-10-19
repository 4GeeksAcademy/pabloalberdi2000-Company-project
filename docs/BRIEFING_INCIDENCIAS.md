# BRIEFING - Sistema de Análisis de Incidencias Postventa Brasaland

## Contexto
Brasaland necesita analizar incidencias postventa de sus 14 locales en Colombia y Florida para mejorar la experiencia del cliente y la eficiencia operativa.

## Estructura del CSV

### Campos Obligatorios
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id_incidencia` | string | Identificador único de la incidencia |
| `fecha` | date (YYYY-MM-DD) | Fecha de registro |
| `categoria` | string | Categoría de la incidencia |
| `descripcion` | string | Descripción del problema |
| `estado` | string | Estado actual de la incidencia |
| `local` | string | Local donde ocurrió |
| `pais` | string | País del local (CO/US) |

### Campos Opcionales
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `satisfaccion` | integer | Puntuación de satisfacción (1-5), requerido si estado es "cerrado" |
| `email_cliente` | string | Email del cliente (PII - no analizar) |
| `telefono` | string | Teléfono del cliente (PII - no analizar) |

---

## Valores Permitidos

### Categorías
- `calidad_comida` - Problemas con sabor, cocción, temperatura, presentación
- `servicio_cliente` - Atención del personal, tiempos de espera, trato
- `operaciones` - Problemas logísticos, stock, proveedores
- `infraestructura` - Equipos, instalaciones, limpieza
- `pedidos_online` - Problemas con app o web
- `facturacion` - Errores en cuentas, cobros

### Estados
- `abierto` - Incidencia reportada, pendiente de atención
- `en_proceso` - Se está trabajando en la solución
- `cerrado` - Incidencia resuelta
- `descartado` - Incidencia no procede o duplicada

### Países
- `CO` - Colombia (10 locales)
- `US` - Florida, Estados Unidos (4 locales)

### Locales Colombia (CO)
- `medellin_centro`
- `medellin_poblado`
- `medellin_envigado`
- `bogota_zona_rosa`
- `bogota_usaquen`
- `bogota_suba`
- `cali_norte`
- `cali_sur`
- `cartagena_centro`
- `barranquilla_norte`

### Locales Florida (US)
- `miami_beach`
- `miami_downtown`
- `orlando_international`
- `tampa_centro`

### Satisfacción (solo para casos cerrados)
- `1` - Muy insatisfecho
- `2` - Insatisfecho
- `3` - Neutral
- `4` - Satisfecho
- `5` - Muy satisfecho

---

## Reglas de Validación

### Registros Inválidos
Un registro se considera **inválido** si:
1. Falta algún campo obligatorio
2. La categoría no está en la lista permitida
3. El estado no está en la lista permitida
4. El país no es 'CO' o 'US'
5. El local no existe en la lista
6. El estado es "cerrado" pero falta el campo `satisfaccion`
7. El campo `satisfaccion` existe pero está fuera del rango 1-5
8. La fecha no tiene formato válido YYYY-MM-DD

### Registros Válidos
- Se incluyen en el análisis de métricas
- Deben cumplir todas las reglas de validación

---

## Métricas a Calcular

### Resumen General
- Total de registros procesados
- Registros válidos
- Registros inválidos

### Por Categoría (solo válidos)
Conteo de incidencias por cada categoría

### Por Estado (solo válidos)
Conteo de incidencias por cada estado

### Por País (solo válidos)
Conteo de incidencias por país (CO vs US)

### Índice de Satisfacción
- Promedio de puntuaciones de satisfacción
- Solo para casos en estado "cerrado" con puntuación válida
- Rango: 1.0 - 5.0

---

## Ejemplo de CSV Válido

```csv
id_incidencia,fecha,categoria,descripcion,estado,local,pais,satisfaccion,email_cliente,telefono
INC001,2026-10-15,calidad_comida,Carne poco cocida,cerrado,medellin_centro,CO,4,cliente@email.com,+573001234567
INC002,2026-10-16,servicio_cliente,Tiempo de espera excesivo,en_proceso,miami_beach,US,,cliente2@email.com,+1234567890
INC003,2026-10-17,pedidos_online,App no carga menú,abierto,bogota_zona_rosa,CO,,,
INC004,2026-10-17,calidad_comida,Porción pequeña,cerrado,miami_downtown,US,3,cliente4@email.com,
```

---

**Responsable:** Nicolás Park (CTO - Brasaland Digital)  
**Departamento:** Tecnología + Operaciones  
**Versión:** 1.0  
**Fecha:** Octubre 2026
