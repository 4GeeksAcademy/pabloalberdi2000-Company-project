# Skill: Validar CSV de Incidencias - Brasaland

**Nombre**: `validate-incident-csv`  
**Alcance**: 🟡 **Bajo demanda** (activar con comando o cuando se mencione validación de incidencias)  
**Categoría**: Data Validation  
**Duración estimada**: 30 segundos

---

## Objetivo

Validar que un archivo CSV de incidencias postventa cumple con las especificaciones del BRIEFING de Brasaland antes de procesarlo en el sistema, detectando errores tempranos y proporcionando feedback claro al usuario.

---

## Inputs

### Requeridos
1. **`csv_file_path`** (string)
   - Ruta al archivo CSV a validar
   - Ejemplo: `scripts/test-incidents.csv`
   - Formato: UTF-8, headers en primera línea

### Opcionales
2. **`verbose`** (boolean, default: `false`)
   - Si es `true`, muestra detalles de cada validación
   - Si es `false`, solo muestra resumen

3. **`export_report`** (boolean, default: `false`)
   - Si es `true`, genera reporte de validación en `validation-report.txt`

---

## Proceso de Ejecución

### Paso 1: Verificar existencia del archivo
```bash
if [ ! -f "$csv_file_path" ]; then
  echo "❌ Error: Archivo no encontrado: $csv_file_path"
  exit 1
fi
```

### Paso 2: Ejecutar script de análisis
```bash
python scripts/analyze.py "$csv_file_path"
```

### Paso 3: Interpretar resultados

El script retorna:
- **Exit code 0**: Validación exitosa
- **Exit code 1**: Archivo con errores

Capturar output para análisis:
```
Total de registros procesados: X
✅ Registros válidos: Y
❌ Registros inválidos: Z
```

### Paso 4: Reportar al usuario

#### Si todos los registros son válidos:
```
✅ Validación exitosa
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Archivo: test-incidents.csv
✓ Registros procesados: 10
✓ Registros válidos: 10
✓ Registros inválidos: 0

🟢 El archivo cumple con todas las especificaciones del BRIEFING.
Puedes proceder a subirlo al sistema.
```

#### Si hay registros inválidos:
```
⚠️ Validación con errores
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Archivo: incidents-2026-10.csv
✓ Registros procesados: 50
✓ Registros válidos: 47
❌ Registros inválidos: 3

🔴 Errores detectados:

  Línea 15 | ID: INC014 | Campo obligatorio faltante: categoria
  Línea 23 | ID: INC022 | Local inválido: miami_centro
  Línea 41 | ID: INC040 | Estado 'cerrado' requiere campo 'satisfaccion'

📝 Recomendación:
Corrige los 3 errores antes de subir el archivo al sistema.
```

---

## Validaciones Específicas

Esta skill verifica los siguientes criterios del BRIEFING:

### ✅ Campos Obligatorios
- `id_incidencia`
- `fecha` (formato YYYY-MM-DD)
- `categoria`
- `descripcion`
- `estado`
- `local`
- `pais`

### ✅ Categorías Permitidas (6)
- `calidad_comida`
- `servicio_cliente`
- `operaciones`
- `infraestructura`
- `pedidos_online`
- `facturacion`

### ✅ Estados Permitidos (4)
- `abierto`
- `en_proceso`
- `cerrado`
- `descartado`

### ✅ Países Permitidos (2)
- `CO` (Colombia)
- `US` (Estados Unidos / Florida)

### ✅ Locales Permitidos (14)
**Colombia (10)**:
- medellin_centro, medellin_poblado, medellin_envigado
- bogota_zona_rosa, bogota_usaquen, bogota_suba
- cali_norte, cali_sur
- cartagena_centro, barranquilla_norte

**Florida (4)**:
- miami_beach, miami_downtown
- orlando_international, tampa_centro

### ✅ Reglas de Negocio
- Si `estado` es `"cerrado"`, debe tener `satisfaccion` (1-5)
- `satisfaccion` debe estar en rango 1-5
- Fecha debe tener formato YYYY-MM-DD válido

---

## Criterios de Aceptación

### ✅ Skill exitosa si:
1. El archivo CSV existe y es legible
2. Se ejecuta el script de análisis sin errores de ejecución
3. Se muestra resumen claro con total procesados/válidos/inválidos
4. Si hay errores, se listan con: línea, ID y razón específica
5. Se da recomendación clara al usuario (proceder o corregir)

### ❌ Skill falla si:
1. El archivo no existe o no es accesible
2. El script de análisis tiene error de sintaxis
3. No se puede parsear el CSV (encoding, formato)

---

## Ejemplo de Uso

### Comando
```bash
# En conversación con el agente:
"Valida el archivo incidents-brasaland-oct.csv"
```

### Ejecución interna
```bash
python scripts/analyze.py incidents-brasaland-oct.csv
```

### Output esperado
```
🔍 Analizando incidencias...

======================================================================
  ANÁLISIS DE INCIDENCIAS POSTVENTA - BRASALAND
======================================================================

📊 RESUMEN GENERAL
----------------------------------------------------------------------
  Total de registros procesados: 25
  ✅ Registros válidos:           23
  ❌ Registros inválidos:         2

❌ REGISTROS INVÁLIDOS DETECTADOS
----------------------------------------------------------------------
  Línea 12 | ID: INC011 | Categoría inválida: servicio_rapido
  Línea 19 | ID: INC018 | Satisfacción fuera de rango (1-5): 6

✅ Análisis completado
```

---

## Integración con Flujo de Trabajo

### Cuándo usar esta skill:
1. **Antes de subir CSV al frontend** - Validación preventiva
2. **Debugging de errores** - Identificar problema específico
3. **Revisión de calidad** - Verificar datos de terceros
4. **Onboarding de usuarios** - Enseñar formato correcto

### No usar para:
- Análisis completo con métricas (usar sistema web)
- Exportación de resultados (usar `--export`)
- Datos ya en el sistema (usar API)

---

## Archivos Relacionados

- **Script**: `scripts/analyze.py`
- **BRIEFING**: `docs/BRIEFING_INCIDENCIAS.md`
- **Documentación**: `scripts/ANALYZE_INCIDENTS_README.md`
- **Datos de prueba**: `scripts/test-incidents.csv`

---

## Notas Técnicas

### Dependencias
- Python 3.7+ (solo stdlib)
- Acceso a filesystem
- Permisos de lectura en archivo CSV

### Performance
- Procesa ~1000 registros en < 1 segundo
- Sin límite de tamaño (memoria eficiente)

### Limitaciones
- Solo valida estructura y reglas, no analiza patrones
- No verifica PII (email, teléfono) por diseño
- No persiste resultados (solo output)

---

**Creada por**: Nicolás Park (CTO)  
**Última actualización**: 19 de Octubre, 2026  
**Versión**: 1.0
