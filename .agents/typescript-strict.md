# Regla: TypeScript Strict Mode - Brasaland

**Alcance**: 🟢 **Siempre activa** para archivos `*.ts` y `*.tsx`  
**Prioridad**: Alta  
**Aplicable a**: `uis/backoffice/**/*.{ts,tsx}`

---

## Objetivo

Garantizar que todo el código TypeScript del frontend de Brasaland cumpla con el modo estricto de TypeScript, evitando errores de tipos en runtime y manteniendo la calidad del código.

---

## Reglas Específicas

### 1. No usar `any`
```typescript
// ❌ INCORRECTO
function processData(data: any) {
  return data.map((item: any) => item.value);
}

// ✅ CORRECTO
interface DataItem {
  value: string;
}

function processData(data: DataItem[]) {
  return data.map((item) => item.value);
}
```

**Excepciones permitidas**:
- `any` en tipos de terceros sin definiciones (`@ts-ignore` documentado)
- Migraciones graduales (con TODO y fecha límite)

---

### 2. Tipos explícitos en funciones públicas
```typescript
// ❌ INCORRECTO
export function getCandidates(params) {
  // ...
}

// ✅ CORRECTO
export async function getCandidates(params?: {
  status?: Status;
  stage?: Stage;
  search?: string;
}): Promise<Candidate[]> {
  // ...
}
```

**Aplicable a**:
- Todas las funciones exportadas
- Props de componentes React
- Funciones de API client (`lib/api.ts`)

---

### 3. Interfaces para objetos complejos
```typescript
// ❌ INCORRECTO
const candidate = {
  full_name: "Juan Pérez",
  country: "CO",
  status: "activo"
};

// ✅ CORRECTO
interface Candidate {
  full_name: string;
  country: Country;
  status: Status;
}

const candidate: Candidate = {
  full_name: "Juan Pérez",
  country: "CO",
  status: "activo"
};
```

**Ubicación**: `uis/backoffice/types/index.ts`

---

### 4. Type guards para unknown
```typescript
// ❌ INCORRECTO
function handleError(error: unknown) {
  alert(error.message); // Error: Property 'message' does not exist on type 'unknown'
}

// ✅ CORRECTO
function handleError(error: unknown) {
  const message = error instanceof Error ? error.message : 'Error desconocido';
  alert(message);
}
```

---

### 5. Strict null checks
```typescript
// ❌ INCORRECTO
function formatDate(date: Date) {
  return date.toISOString(); // ¿Qué pasa si date es null?
}

// ✅ CORRECTO
function formatDate(date: Date | null): string {
  return date ? date.toISOString() : 'N/A';
}
```

---

### 6. Enums vs Literal Types

**Preferir literal types** (union types):
```typescript
// ✅ PREFERIDO (más simple)
export type Status = 'activo' | 'archivado' | 'contratado' | 'rechazado';
export type Country = 'CO' | 'US';

// ⚠️ Usar solo si necesitas valores numéricos o métodos
export enum Stage {
  Aplicacion = 'aplicacion',
  Revision = 'revision',
  Entrevista = 'entrevista',
  Oferta = 'oferta',
  Finalizado = 'finalizado'
}
```

---

## Verificación Automatizada

### Pre-commit
```bash
cd uis/backoffice
npx tsc --noEmit  # Type checking sin generar archivos
```

**Criterio de aprobación**: Cero errores de TypeScript

### VSCode
Configurar `tsconfig.json`:
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true
  }
}
```

---

## Casos Especiales de Brasaland

### Tipos de Datos del Negocio

```typescript
// Types centralizados en types/index.ts
export type Country = 'CO' | 'US';
export type Status = 'activo' | 'archivado' | 'contratado' | 'rechazado';
export type Stage = 'aplicacion' | 'revision' | 'entrevista' | 'oferta' | 'finalizado';

// Puestos específicos de restaurante
export const POSITION_OPTIONS = [
  'Cocinero',
  'Ayudante de Cocina',
  'Mesero',
  'Cajero',
  'Supervisor de Local',
  'Gerente de Local'
] as const;

export type Position = typeof POSITION_OPTIONS[number];

// Locales de Brasaland
export type LocalColombia = 
  | 'medellin_centro' 
  | 'medellin_poblado'
  // ... resto de locales
;

export type LocalFlorida = 
  | 'miami_beach'
  | 'miami_downtown'
  | 'orlando_international'
  | 'tampa_centro'
;

export type Local = LocalColombia | LocalFlorida;
```

---

## Excepciones Documentadas

### JSON parsing
```typescript
// OK: JSON.parse retorna 'any', pero inmediatamente tipar
const response = await fetch('/api/endpoint');
const data = await response.json() as Candidate[];
```

### Event handlers
```typescript
// OK: Event handlers pueden inferir tipo del contexto
const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
  e.preventDefault();
};

// También OK si el tipo es obvio:
<button onClick={(e) => e.preventDefault()}>Click</button>
```

---

## Métricas de Cumplimiento

**Target**: 100% de archivos TypeScript sin errores  
**Actual**: 100% (ATS + Incidencias)  
**Revisión**: En cada PR

---

## Recursos

- [TypeScript Handbook - Strict Mode](https://www.typescriptlang.org/tsconfig#strict)
- [Brasaland Types](../uis/backoffice/types/index.ts)
- [Tech Context](../memory-bank/techContext.md#typescript)
