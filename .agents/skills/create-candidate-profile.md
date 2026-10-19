# Skill: Crear Perfil de Candidato - Brasaland ATS

**Nombre**: `create-candidate-profile`  
**Alcance**: 🟡 **Bajo demanda** (cuando se mencione creación de candidato o onboarding RRHH)  
**Categoría**: RRHH / ATS  
**Duración estimada**: 1-2 minutos

---

## Objetivo

Crear un nuevo perfil de candidato en el sistema ATS de Brasaland de forma estructurada, validando que todos los campos obligatorios estén completos y siguiendo las convenciones del negocio (puestos específicos, países, locales).

---

## Inputs

### Requeridos
1. **`full_name`** (string)
   - Nombre completo del candidato
   - Mínimo 3 caracteres
   - Ejemplo: "María Fernanda Gómez"

2. **`email`** (string)
   - Email válido (formato validado)
   - Debe ser único en el sistema
   - Ejemplo: "maria.gomez@email.com"

3. **`phone`** (string)
   - Número de teléfono con código de país
   - Colombia: +57 3XX XXX XXXX
   - USA: +1 XXX XXX XXXX
   - Ejemplo: "+57 300 123 4567"

4. **`position`** (string)
   - Puesto solicitado (solo opciones válidas de Brasaland)
   - Opciones: Cocinero, Ayudante de Cocina, Mesero, Cajero, Supervisor de Local, Gerente de Local
   - Ejemplo: "Cocinero"

5. **`country`** (enum: CO | US)
   - País donde aplicó
   - `CO` = Colombia
   - `US` = Florida, Estados Unidos
   - Ejemplo: "CO"

6. **`years_experience`** (integer)
   - Años de experiencia en el puesto
   - Mínimo: 0, Máximo: 50
   - Ejemplo: 3

### Opcionales
7. **`location_preference`** (string)
   - Local específico de preferencia
   - Debe ser uno de los 14 locales de Brasaland
   - Ejemplo: "Medellín Centro" o "Miami Beach"

8. **`linkedin_url`** (string)
   - URL completa del perfil de LinkedIn
   - Formato: https://linkedin.com/in/...
   - Ejemplo: "https://linkedin.com/in/maria-gomez"

9. **`cv_url`** (string)
   - URL de Google Drive, Dropbox, etc. con el CV
   - Ejemplo: "https://drive.google.com/file/d/..."

---

## Proceso de Ejecución

### Paso 1: Validar Inputs

```typescript
// Validaciones obligatorias
const errors: string[] = [];

if (!full_name || full_name.trim().length < 3) {
  errors.push("El nombre debe tener al menos 3 caracteres");
}

if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
  errors.push("Email inválido");
}

if (!phone) {
  errors.push("El teléfono es obligatorio");
}

const validPositions = [
  'Cocinero',
  'Ayudante de Cocina',
  'Mesero',
  'Cajero',
  'Supervisor de Local',
  'Gerente de Local'
];

if (!validPositions.includes(position)) {
  errors.push(`Puesto inválido. Debe ser uno de: ${validPositions.join(', ')}`);
}

if (!['CO', 'US'].includes(country)) {
  errors.push("País debe ser 'CO' o 'US'");
}

if (years_experience < 0 || years_experience > 50) {
  errors.push("Años de experiencia fuera de rango (0-50)");
}

if (errors.length > 0) {
  return { success: false, errors };
}
```

### Paso 2: Preparar Payload

```typescript
const candidateData = {
  full_name,
  email,
  phone,
  position,
  country,
  years_experience,
  location_preference: location_preference || '',
  linkedin_url: linkedin_url || '',
  cv_url: cv_url || '',
  application_date: new Date().toISOString().split('T')[0], // YYYY-MM-DD
  status: 'activo',  // Estado inicial
  stage: 'aplicacion' // Etapa inicial
};
```

### Paso 3: Enviar a API

```bash
# Opción 1: Usar API directamente (si backend está corriendo)
curl -X POST "http://localhost:8000/records" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "María Fernanda Gómez",
    "email": "maria.gomez@email.com",
    "phone": "+57 300 123 4567",
    "position": "Cocinero",
    "country": "CO",
    "location_preference": "Medellín Centro",
    "years_experience": 3,
    "application_date": "2026-10-19"
  }'

# Opción 2: Usar frontend (si está corriendo)
# Abrir http://localhost:3000/new y llenar formulario
```

### Paso 4: Confirmar Creación

Si la respuesta es exitosa (status 201):
```json
{
  "id": 42,
  "full_name": "María Fernanda Gómez",
  "email": "maria.gomez@email.com",
  "status": "activo",
  "stage": "aplicacion",
  // ... resto de campos
}
```

---

## Output Esperado

### ✅ Creación exitosa:
```
✅ Candidato creado exitosamente
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Detalles del candidato:

  ID:                #42
  Nombre:            María Fernanda Gómez
  Email:             maria.gomez@email.com
  Teléfono:          +57 300 123 4567
  
  Puesto:            Cocinero
  País:              Colombia
  Local preferido:   Medellín Centro
  Experiencia:       3 años
  
  Estado:            Activo
  Etapa:             Aplicación
  Fecha aplicación:  19/10/2026

🔗 Ver perfil completo:
   http://localhost:3000/candidates/42

📝 Próximos pasos:
   1. Revisar CV y LinkedIn
   2. Programar entrevista telefónica
   3. Actualizar etapa a "Revisión"
```

### ❌ Error de validación:
```
❌ No se pudo crear el candidato
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Errores encontrados:
  • Email inválido: falta el dominio
  • Puesto inválido. Debe ser uno de: Cocinero, Mesero, Cajero, ...
  
Por favor corrige estos errores e intenta nuevamente.
```

---

## Criterios de Aceptación

### ✅ Skill exitosa si:
1. Se validan todos los campos obligatorios
2. Se verifica que el puesto esté en la lista de Brasaland
3. Se asigna automáticamente estado "activo" y etapa "aplicacion"
4. Se genera fecha de aplicación (hoy)
5. Se crea el registro en la base de datos
6. Se retorna ID del candidato creado
7. Se muestra URL para ver perfil completo
8. Se sugieren próximos pasos al usuario (Ashley Turner)

### ❌ Skill falla si:
1. Faltan campos obligatorios sin avisar
2. No se validan formatos (email, teléfono)
3. Se acepta un puesto que no existe en Brasaland
4. No se maneja el caso de email duplicado

---

## Casos Especiales de Brasaland

### Puestos por Área

**Cocina** (alta rotación):
- Cocinero
- Ayudante de Cocina

**Sala** (contacto con cliente):
- Mesero
- Cajero

**Gestión** (bajo turnover):
- Supervisor de Local
- Gerente de Local

### Preferencias de Local

Si el candidato especifica local preferido, validar que exista:

**Colombia (10 locales)**:
- Medellín: Centro, Poblado, Envigado
- Bogotá: Zona Rosa, Usaquén, Suba
- Cali: Norte, Sur
- Otros: Cartagena Centro, Barranquilla Norte

**Florida (4 locales)**:
- Miami: Beach, Downtown
- Orlando: International Drive
- Tampa: Centro

### Flujo de RRHH

Estados del candidato:
1. **Activo** - En proceso de selección
2. **Archivado** - No seleccionado, mantener para futuros procesos
3. **Contratado** - Proceso exitoso
4. **Rechazado** - No cumple requisitos

Etapas del proceso:
1. **Aplicación** - Candidato recién ingresado
2. **Revisión** - RRHH revisando perfil
3. **Entrevista** - Entrevista programada/realizada
4. **Oferta** - Oferta laboral enviada
5. **Finalizado** - Proceso cerrado (contratado o rechazado)

---

## Integración con Flujo de Trabajo

### Cuándo usar esta skill:
1. **Nuevo candidato por referido** - Alguien del equipo refiere a un conocido
2. **Walk-in** - Candidato llega al local y deja CV
3. **Migración de Excel** - Traspasar candidatos del sistema antiguo
4. **Batch creation** - Procesar varios candidatos de evento de reclutamiento

### No usar para:
- Actualizar candidato existente (usar `PUT /records/{id}`)
- Cambiar solo estado/etapa (usar `PATCH /records/{id}/status` o `/stage`)
- Agregar notas (usar `POST /records/{id}/notes`)

---

## Archivos Relacionados

- **Frontend**: `uis/backoffice/app/new/page.tsx`
- **Backend**: `services/api/app/routers/candidates.py` (POST /records)
- **Types**: `uis/backoffice/types/index.ts`
- **API Client**: `uis/backoffice/lib/api.ts` (createCandidate function)

---

## Notas Técnicas

### Validación de Email Único
El backend valida que el email no exista:
```python
# services/api/app/routers/candidates.py
existing = db.query(Candidate).filter(Candidate.email == email).first()
if existing:
    raise HTTPException(status_code=400, detail="Email ya existe en el sistema")
```

### Application Date
Siempre se usa la fecha actual del servidor (no del cliente):
```python
application_date = date.today()
```

### País vs Locales
- País determina legislación laboral aplicable
- Local preferido es opcional y puede cambiar
- Un candidato CO puede trabajar en cualquier local CO (movilidad)

---

**Creada por**: Ashley Turner (RRHH) + Nicolás Park (CTO)  
**Última actualización**: 19 de Octubre, 2026  
**Versión**: 1.0
