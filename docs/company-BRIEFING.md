# Company Briefing - Brasaland Digital

**Empresa**: Brasaland  
**Sector**: Restaurantes - Cocina a la brasa  
**Locales**: 14 (10 Colombia + 4 Florida, USA)  
**Empleados**: 115  
**Facturación anual**: $6M USD  
**CEO**: Mariana Restrepo

---

## 🧑‍💼 Responsables por Departamento (Human-in-the-Loop Approvers)

| Departamento | Responsable | Rol | Email | País Base |
|--------------|-------------|-----|-------|-----------|
| **Operaciones** | Felipe Guerrero | Director de Operaciones | felipe.guerrero@brasaland.com | Colombia |
| **Tecnología** | Nicolás Park | CTO | nicolas.park@brasaland.com | Colombia |
| **Marketing** | Camila Ospina | Head of Marketing | camila.ospina@brasaland.com | Colombia |
| **Compras** | Lucía Fernández | Jefa de Compras | lucia.fernandez@brasaland.com | Colombia |
| **RRHH** | Ashley Turner | Directora de Personas y Cultura | ashley.turner@brasaland.com | USA (Miami) |
| **Formación** | Jake Morrison | Jefe de Formación y Estándares | jake.morrison@brasaland.com | USA (Miami) |
| **Dirección** | Mariana Restrepo | CEO | mariana.restrepo@brasaland.com | Colombia |
| **Especiales** | Mariana Restrepo | CEO (Arbitraje Final) | mariana.restrepo@brasaland.com | Colombia |

---

## ⚖️ Reglas de Arbitraje (Conflict Resolution)

### Nivel 1: Conflictos Menores (severity=LOW)
**Resolutor**: Departamento con mayor seniority  
**Tiempo máximo**: 24 horas

### Nivel 2: Conflictos Medios (severity=MEDIUM)
**Resolutor**: CTO (Nicolás Park) para temas técnicos, CEO para temas de negocio  
**Tiempo máximo**: 48 horas

### Nivel 3: Conflictos Críticos (severity=HIGH)
**Resolutor**: CEO (Mariana Restrepo)  
**Tiempo máximo**: 72 horas  
**Requiere**: Junta con ambos departamentos + CEO

### Nivel 4: Deadlock Total (severity=CRITICAL)
**Resolutor**: CEO (Mariana Restrepo) + Junta Directiva  
**Tiempo máximo**: 1 semana  
**Requiere**: Presentación formal de ambas posturas + propuesta de resolución

---

## 🚨 Departamento "Especiales"

Proyectos que NO encajan en las 6 áreas estándar se asignan a "Especiales" y son revisados directamente por la CEO.

**Ejemplos**:
- Proyectos legales/regulatorios
- Alianzas estratégicas
- Cambios de estructura organizacional
- Inversiones mayores (>$100K USD)

---

## 📋 Proceso de Aprobación Humana (HITL)

### Paso 1: Pre-Aprobación
- Sistema genera borrador técnico y económico
- Auto-evaluación con rúbricas (Parte 2)
- Si pasa evaluación → Envía a aprobador humano
- Si NO pasa → Marca como "needs_human_review"

### Paso 2: Interrupción (interrupt)
- Grafo LangGraph se pausa ANTES del nodo de aprobación
- Se guarda checkpoint en PostgreSQL/Supabase
- Notificación al responsable vía email/Slack (futuro)
- Estado ticket: `esperando_aprobación`

### Paso 3: Revisión Humana
- Responsable revisa en UI dedicada (futuro frontend)
- Opciones:
  - ✅ **Aprobar**: Continúa flujo
  - ❌ **Rechazar**: Regresa a generación (Parte 2)
  - 🔄 **Solicitar cambios**: Regresa con feedback específico

### Paso 4: Reanudación (resume)
- Endpoint `POST /rfp/approval/{ticket_id}/approve/{department}`
- Decisión se inyecta en checkpoint vía `update_state()`
- Grafo reanuda EXACTAMENTE donde se detuvo (NO reinicia)
- Continúa con siguiente departamento en paralelo

### Paso 5: Barrier
- Cuando TODOS los departamentos aprueban → Continúa
- Si alguno rechaza → Escala a arbitraje o regresa a generación

---

## 🔐 Niveles de Autoridad

| Rango de Presupuesto | Aprobador Requerido |
|-----------------------|---------------------|
| < $10K USD | Jefe de departamento |
| $10K - $50K USD | CTO o Director Operaciones |
| $50K - $100K USD | CEO |
| > $100K USD | CEO + Junta Directiva |

---

## 📞 Contactos de Emergencia

**CTO (Nicolás Park)**: +57 300 123 4567 (WhatsApp)  
**CEO (Mariana Restrepo)**: +57 310 987 6543 (WhatsApp)  
**Director Operaciones (Felipe)**: +57 320 555 1234

---

## 🌍 Zonas Horarias

- **Colombia**: UTC-5 (COT - Colombia Time)
- **Florida**: UTC-5 (EST) / UTC-4 (EDT)

**Horario laboral**: 9:00 AM - 6:00 PM hora local  
**Respuestas de aprobación esperadas**: < 48 horas hábiles

---

**Última actualización**: 2026-11-17  
**Versión**: 1.0  
**Responsable de documento**: Nicolás Park (CTO)
