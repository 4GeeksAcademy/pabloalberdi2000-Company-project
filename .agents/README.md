# Configuración de Agentes - Brasaland Digital

Esta carpeta contiene las reglas y skills para agentes IA que trabajan en el monorepo de Brasaland.

---

## 📁 Estructura

```
.agents/
├── README.md                           # Este archivo
├── typescript-strict.md                # Regla: TypeScript modo estricto
└── skills/
    ├── validate-incident-csv.md        # Skill: Validar CSV de incidencias
    └── create-candidate-profile.md     # Skill: Crear perfil de candidato
```

---

## 🔧 Reglas Disponibles

### `typescript-strict.md`
**Alcance**: 🟢 Siempre activa para `*.ts` y `*.tsx`

Garantiza que todo el código TypeScript cumpla modo estricto:
- No usar `any`
- Tipos explícitos en funciones públicas
- Interfaces para objetos complejos
- Type guards para `unknown`
- Strict null checks

---

## 🎯 Skills Disponibles

### `validate-incident-csv`
**Alcance**: 🟡 Bajo demanda

Valida un archivo CSV de incidencias contra especificaciones del BRIEFING:
- Verifica campos obligatorios
- Valida categorías (6), estados (4), países (2), locales (14)
- Detecta registros inválidos con razón específica
- Genera reporte claro para el usuario

**Uso**: "Valida el archivo incidents-oct.csv"

---

### `create-candidate-profile`
**Alcance**: 🟡 Bajo demanda

Crea un nuevo perfil de candidato en el ATS:
- Valida campos obligatorios y formatos
- Verifica puestos específicos de Brasaland
- Asigna estado "activo" y etapa "aplicacion"
- Retorna ID y URL del perfil creado

**Uso**: "Crea un candidato con nombre X, email Y..."

---

## 📚 Documentación Relacionada

- **Protocolo general**: `/AGENTS.md`
- **Memory bank**: `/memory-bank/`
  - `projectbrief.md` - Contexto del negocio
  - `techContext.md` - Stack técnico
  - `progress.md` - Estado del proyecto

---

## 🆕 Agregar Nueva Regla

1. Crear archivo `.agents/nombre-regla.md`
2. Especificar **alcance** (siempre/patrón/demanda)
3. Documentar objetivo y reglas específicas
4. Incluir ejemplos correcto/incorrecto
5. Definir criterios de verificación

**Plantilla**:
```markdown
# Regla: Nombre Descriptivo

**Alcance**: 🟢 Siempre activa / 🟡 Patrón / 🔵 Bajo demanda  
**Prioridad**: Alta/Media/Baja

## Objetivo
[Por qué existe esta regla]

## Reglas Específicas
[Lista numerada de reglas]

## Verificación
[Cómo comprobar cumplimiento]
```

---

## 🆕 Agregar Nueva Skill

1. Crear archivo `.agents/skills/nombre-skill.md`
2. Documentar **objetivo único y claro**
3. Especificar **inputs** (requeridos y opcionales)
4. Detallar **proceso de ejecución**
5. Definir **criterios de aceptación**
6. Incluir **casos especiales de Brasaland**

**Plantilla**:
```markdown
# Skill: Nombre Descriptivo

**Nombre**: `nombre-skill`
**Alcance**: 🟡 Bajo demanda
**Categoría**: Área
**Duración estimada**: X min

## Objetivo
[Qué hace esta skill]

## Inputs
### Requeridos
1. **param1** (type) - descripción

### Opcionales
2. **param2** (type) - descripción

## Proceso de Ejecución
[Pasos detallados]

## Criterios de Aceptación
[Cuándo la skill es exitosa]
```

---

## ✅ Checklist de Calidad

Toda regla/skill debe:
- [ ] Tener objetivo claro y único
- [ ] Usar terminología de Brasaland (locales, puestos, categorías reales)
- [ ] Incluir ejemplos concretos
- [ ] Especificar criterios de éxito/fallo
- [ ] Referenciar archivos del proyecto
- [ ] Estar alineada con `memory-bank/`

---

**Mantenido por**: Nicolás Park (CTO)  
**Última actualización**: 19 de Octubre, 2026
