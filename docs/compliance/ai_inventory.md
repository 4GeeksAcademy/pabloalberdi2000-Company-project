# 🤖 Inventario de Sistemas de IA y Gobierno - Brasaland Digital

**Fecha**: 2026-10-31  
**Responsable de Compliance**: Tech Lead + Compliance Officer  
**Marco Regulatorio**: NIST AI RMF 1.0 + GDPR + Florida CCPA  
**Revisión**: Trimestral obligatoria

---

## 📋 Resumen Ejecutivo

**Total de Componentes de IA**: 8 sistemas activos  
**Modelos LLM Externos**: 2 proveedores (OpenAI, Anthropic)  
**Bases de Datos Vectoriales**: 1 (Qdrant)  
**Servidores MCP**: 1 (Tools de Soporte/Inventario)  
**Workflows Multi-Agente**: 4 (RFP Intake, Generation, Approval, Business Performance)

### Clasificación de Riesgo

| Nivel | Componentes | % Total |
|-------|-------------|---------|
| 🔴 **Alto** | 3 | 37.5% |
| 🟡 **Medio** | 4 | 50% |
| 🟢 **Bajo** | 1 | 12.5% |

---

## 🎯 Marco Regulatorio y Compliance (COMPANY-BRIEFING.md)

### Datos Procesados y Jurisdicciones

**Negocio**: Cadena de restaurantes Brasaland  
- **14 locales**: 10 Colombia + 4 Florida (USA)
- **115 empleados**: Multi-jurisdicción (Colombia + Florida)
- **Facturación**: $6M USD/año

### Regulaciones Aplicables

#### 1. **GDPR (General Data Protection Regulation)**

**Aplicabilidad**: ❌ **NO APLICA DIRECTAMENTE**

**Razón**: 
- Brasaland NO opera en la Unión Europea
- NO tiene clientes en UE
- NO procesa datos de ciudadanos UE

**Consideración**: Si en el futuro se expande a España u otro país UE, GDPR será obligatorio.

---

#### 2. **CCPA/CPRA (California Consumer Privacy Act)**

**Aplicabilidad**: ⚠️ **APLICA PARCIALMENTE**

**Razón**:
- Brasaland opera en **Florida** (NO California)
- Florida tiene su propia legislación de privacidad: **Florida Information Protection Act (FIPA)**

**Regulación Florida (FIPA)**:
- **Ley**: Florida Statutes § 501.171
- **Requisitos**:
  - Notificación de brechas de datos dentro de **30 días**
  - Cifrado de PII (Personally Identifiable Information)
  - Procedimientos de seguridad razonables
  - Derecho de notificación al afectado

**Datos PII Procesados en Florida**:
- Nombres y apellidos de empleados
- Emails corporativos
- Números de teléfono
- Información de candidatos (ATS)
- Datos de clientes con programa de fidelización (cuando se implemente)

---

#### 3. **Colombia - Ley 1581 de 2012 (Habeas Data)**

**Aplicabilidad**: ✅ **APLICA OBLIGATORIAMENTE**

**Razón**:
- 10 locales en Colombia
- ~70% de empleados en Colombia
- Datos de clientes colombianos

**Requisitos Ley 1581**:
1. **Consentimiento Informado**: Autorización explícita para procesamiento de datos
2. **Finalidad**: Los datos solo pueden usarse para el propósito autorizado
3. **Derecho de Acceso**: Los titulares pueden consultar sus datos
4. **Derecho de Rectificación**: Corregir datos inexactos
5. **Derecho de Supresión**: Eliminar datos cuando ya no sean necesarios
6. **Seguridad**: Medidas técnicas y administrativas para proteger datos
7. **Notificación de Brechas**: **Inmediata** a la Superintendencia de Industria y Comercio (SIC)

**Datos Personales Procesados en Colombia**:
- Datos de empleados (nómina, contratos)
- Candidatos del ATS
- Clientes con programa de fidelización
- Datos de incidencias postventa (nombres, quejas)

---

#### 4. **SOC 2 Type II**

**Aplicabilidad**: ⏳ **NO REQUERIDO AÚN**

**Razón**:
- Brasaland NO vende servicios SaaS B2B
- Sistema interno para operaciones propias

**Consideración Futura**: Si Brasaland Digital decide vender su plataforma a otras cadenas de restaurantes (SaaS), SOC 2 será obligatorio.

---

### Resumen de Plazos de Notificación de Incidentes

| Jurisdicción | Regulación | Plazo Máximo | Autoridad |
|--------------|------------|--------------|-----------|
| **Colombia** | Ley 1581 (Habeas Data) | **Inmediato** | Superintendencia de Industria y Comercio (SIC) |
| **Florida (USA)** | FIPA (FS § 501.171) | **30 días** | Florida Attorney General |
| **Unión Europea** | GDPR | 72 horas | N/A (no aplica) |

---

### Datos Restringidos y Prohibidos

#### ❌ **Prohibido Procesar por los Sistemas de IA**

1. **Datos Financieros Sensibles**:
   - Números de tarjetas de crédito completos
   - CVV de tarjetas
   - Cuentas bancarias de empleados

2. **Datos de Salud (HIPAA)**:
   - Diagnósticos médicos
   - Historial clínico
   - Incapacidades médicas detalladas

3. **Datos de Menores de Edad**:
   - Información de clientes <18 años (sin consentimiento parental)
   - Datos de hijos de empleados

4. **Datos Biométricos**:
   - Huellas dactilares
   - Reconocimiento facial
   - Datos de voz para identificación

#### ✅ **Permitido Procesar (con Consentimiento)**

1. **Datos de Empleados**:
   - Nombres, emails, teléfonos
   - Información laboral (cargo, local, fecha de contratación)
   - Evaluaciones de desempeño

2. **Datos de Candidatos (ATS)**:
   - CV y hojas de vida
   - Notas de entrevistas
   - Estado del proceso de selección

3. **Datos de Clientes (Programa Fidelización)**:
   - Nombre, email, teléfono
   - Historial de compras
   - Preferencias de menú

4. **Datos Operacionales**:
   - Ventas por local
   - Inventario de materia prima
   - Incidencias de servicio (quejas/reclamos)

---

## 📦 Inventario de Componentes de IA

### 1. RAG (Retrieval-Augmented Generation) - Knowledge Base

**Tipo**: Sistema de Búsqueda Semántica + Generación  
**Riesgo**: 🟡 **MEDIO**  
**Estado**: ✅ Activo

#### Descripción
Sistema de preguntas y respuestas sobre la base de conocimiento de Brasaland (recetas, procedimientos, políticas internas).

#### Componentes Técnicos

| Componente | Tecnología | Versión | Responsable |
|------------|------------|---------|-------------|
| **Modelo LLM** | OpenAI GPT-4o-mini | Última | OpenAI (Tercero) |
| **Embeddings** | OpenAI text-embedding-3-small | 1536 dims | OpenAI (Tercero) |
| **Base Vectorial** | Qdrant | Cloud/Self-hosted | Brasaland Digital |
| **Orquestador** | Python + LangChain | 0.3.x | Brasaland Digital |

#### Archivos Clave
- `data/pipelines/rag_query.py` (Recuperación + Generación)
- `data/process/setup_knowledge_base.py` (Ingesta)
- `data/pipelines/rag_graph.py` (Workflow LangGraph)

#### Datos Procesados
- ✅ Documentos públicos de Brasaland (recetas, procedimientos)
- ✅ Información de locales y menú
- ❌ NO procesa datos personales de empleados/clientes

#### Superficie de Ataque
1. **Prompt Injection**: Usuario malicioso intenta manipular prompts del sistema
2. **Data Poisoning**: Documentos maliciosos insertados en la base de conocimiento
3. **Exfiltración de Contexto**: LLM revela información de otros queries en el contexto

#### Matriz de Responsabilidad Compartida

| Responsabilidad | Brasaland Digital | OpenAI (Tercero) |
|-----------------|-------------------|------------------|
| **Seguridad del Modelo** | ❌ | ✅ |
| **Disponibilidad del Servicio** | ❌ | ✅ |
| **Rate Limiting** | ✅ | ✅ (API limits) |
| **Filtrado de Inputs** | ✅ | ❌ |
| **Aislamiento de Contextos** | ✅ | ❌ |
| **Cifrado de Datos en Tránsito** | ✅ (HTTPS) | ✅ |
| **Auditoría de Prompts** | ✅ | ❌ |
| **Respuesta a Incidentes** | ✅ | ✅ (coordinada) |

#### Controles Actuales
- ✅ API Key en variables de entorno (no hardcodeada)
- ✅ Timeout de 5 segundos en requests
- ❌ **FALTA**: Rate limiting por usuario
- ❌ **FALTA**: Input sanitization
- ❌ **FALTA**: Logging estructurado de prompts

---

### 2. Servidor MCP (Model Context Protocol) - Tools de Soporte

**Tipo**: Servidor de Herramientas con OAuth 2.1  
**Riesgo**: 🔴 **ALTO**  
**Estado**: ✅ Activo

#### Descripción
Servidor MCP que expone herramientas para que agentes de IA puedan crear/actualizar incidencias de soporte y consultar inventario (SOLO LECTURA).

#### Componentes Técnicos

| Componente | Tecnología | Responsable |
|------------|------------|-------------|
| **Framework** | FastMCP | Brasaland Digital |
| **Autenticación** | OAuth 2.1 (mcpauth) | Brasaland Digital |
| **Transporte** | HTTP/SSE (Server-Sent Events) | Brasaland Digital |
| **Backend API** | FastAPI (localhost:8000) | Brasaland Digital |

#### Archivos Clave
- `mcps/server.py` (Servidor MCP principal)
- `mcps/check_dependencies.py` (Validación de dependencias)

#### Tools Expuestos

| Tool | Acción | Riesgo | OAuth Scope |
|------|--------|--------|-------------|
| `create_incident` | Crear incidencia | 🟡 Medio | `incidents:write` |
| `update_incident_status` | Actualizar estado | 🟡 Medio | `incidents:write` |
| `get_incident_status` | Consultar estado | 🟢 Bajo | `incidents:read` |
| `get_inventory_stock` | Consultar inventario | 🟢 Bajo | `inventory:read` |

#### Datos Procesados
- ✅ Incidencias de servicio (ID, estado, descripción)
- ✅ Stock de inventario (productos, cantidades)
- ❌ NO procesa datos personales sensibles

#### Superficie de Ataque
1. **Abuso de Herramientas**: Agente malicioso crea miles de incidencias falsas
2. **Escalación de Privilegios**: Intento de ejecutar tools sin scope OAuth adecuado
3. **Inyección en Parámetros**: Parámetros de tools contienen payloads maliciosos
4. **SSRF**: Tool intenta acceder a endpoints internos no autorizados

#### Matriz de Responsabilidad Compartida

| Responsabilidad | Brasaland Digital |
|-----------------|-------------------|
| **Autenticación OAuth** | ✅ |
| **Validación de Scopes** | ✅ |
| **Rate Limiting por Cliente** | ⏳ Pendiente |
| **Validación de Parámetros** | ✅ (Pydantic) |
| **Auditoría de Tool Calls** | ⏳ Pendiente |
| **Isolation de Tools** | ✅ (lectura != escritura) |

#### Controles Actuales
- ✅ OAuth 2.1 con mcpauth (obligatorio en prod)
- ✅ Inventario en modo SOLO LECTURA (rechaza mutaciones)
- ✅ Validación de parámetros con Pydantic
- ✅ Logging estructurado (structlog)
- ❌ **FALTA**: Rate limiting por cliente OAuth
- ❌ **FALTA**: Auditoría de tool calls en base de datos

---

### 3. Workflow RFP Intake (Ingesta de Propuestas)

**Tipo**: Agente LangGraph Multi-Nodo  
**Riesgo**: 🔴 **ALTO**  
**Estado**: ✅ Activo

#### Descripción
Pipeline que recibe PDFs de solicitudes de propuesta (RFPs), valida si cumplen criterios, extrae información estructurada y clasifica.

#### Componentes Técnicos

| Componente | Tecnología | Responsable |
|------------|------------|-------------|
| **Modelo LLM** | OpenAI GPT-4o-mini | OpenAI (Tercero) |
| **Orquestador** | LangGraph | Brasaland Digital |
| **Parser PDF** | PyMuPDF / pdfplumber | Brasaland Digital |
| **Persistencia** | PostgreSQL | Brasaland Digital |

#### Archivos Clave
- `data/pipelines/rfp_intake/graph.py` (Grafo LangGraph)
- `data/pipelines/rfp_intake/ingest.py` (Ingesta de PDFs)

#### Nodos del Workflow
1. **Parse PDF**: Extrae texto del PDF
2. **Validate RFP**: Verifica si es una RFP válida
3. **Extract Metadata**: Extrae empresa, fecha límite, presupuesto
4. **Classify**: Clasifica por industria y complejidad
5. **Store**: Guarda en base de datos

#### Datos Procesados
- ✅ PDFs de RFPs de clientes potenciales
- ✅ Nombres de empresas, contactos
- ✅ Información de presupuestos
- ⚠️ **RIESGO**: Podría contener datos personales (emails, teléfonos de contactos)

#### Superficie de Ataque
1. **Indirect Prompt Injection**: PDF malicioso contiene instrucciones ocultas que manipulan al agente
2. **Data Exfiltration**: PDF contiene prompts para que el agente revele información interna
3. **Malicious File Upload**: PDF contiene exploits (aunque solo se lee texto, no se ejecuta)
4. **PII Leakage**: Información personal de contactos se loguea sin enmascarar

#### Matriz de Responsabilidad Compartida

| Responsabilidad | Brasaland Digital | OpenAI |
|-----------------|-------------------|--------|
| **Validación de PDFs** | ✅ | ❌ |
| **Sanitización de Texto Extraído** | ⏳ Pendiente | ❌ |
| **Detección de Prompt Injection** | ⏳ Pendiente | ⚠️ Parcial (model guidelines) |
| **Logging de PII** | ⏳ Pendiente (sin masking) | ❌ |
| **Cifrado de PDFs en Reposo** | ⏳ Pendiente | N/A |

#### Controles Actuales
- ✅ Validación de extensión de archivo (.pdf)
- ✅ Timeout en procesamiento (evita PDFs maliciosos que cuelgan)
- ❌ **FALTA**: Validación de magic bytes (MIME type)
- ❌ **FALTA**: Guardrails anti-prompt-injection
- ❌ **FALTA**: Separación de instrucciones del sistema vs contenido del PDF

---

### 4. Workflow RFP Generation (Generación de Propuestas)

**Tipo**: Agente LangGraph Multi-Nodo con Ciclos  
**Riesgo**: 🔴 **ALTO**  
**Estado**: ✅ Activo

#### Descripción
Pipeline que genera propuestas (RFPs) completas iterando entre generación y evaluación hasta cumplir criterios de calidad.

#### Componentes Técnicos

| Componente | Tecnología | Responsable |
|------------|------------|-------------|
| **Generador LLM** | OpenAI GPT-4o-mini | OpenAI (Tercero) |
| **Evaluador LLM** | OpenAI GPT-4o-mini | OpenAI (Tercero) |
| **Orquestador** | LangGraph | Brasaland Digital |
| **Persistencia** | PostgreSQL | Brasaland Digital |

#### Archivos Clave
- `data/pipelines/rfp_generation/graph.py` (Grafo LangGraph)
- `data/pipelines/rfp_generation/generator.py` (Nodo generador)
- `data/pipelines/rfp_generation/evaluators.py` (Nodos evaluadores)

#### Nodos del Workflow
1. **Generate**: Genera borrador de propuesta
2. **Evaluate Quality**: Evalúa claridad, completitud, formato
3. **Evaluate Compliance**: Valida cumplimiento de requerimientos
4. **Decide**: Aprueba o regresa a generar (max 3 iteraciones)
5. **Finalize**: Marca como lista para revisión humana

#### Datos Procesados
- ✅ Requerimientos del cliente (RFP intake)
- ✅ Plantillas de propuestas
- ✅ Información técnica de Brasaland
- ⚠️ **RIESGO**: Podría incluir información sensible (precios, estrategia)

#### Superficie de Ataque
1. **Infinite Loop**: Ciclo generador-evaluador nunca converge (DoS económico)
2. **Cost Amplification**: Adversario manipula inputs para maximizar iteraciones
3. **Data Leakage**: Propuesta generada revela información confidencial de otros clientes
4. **Hallucination**: Generador inventa información falsa sobre Brasaland

#### Matriz de Responsabilidad Compartida

| Responsabilidad | Brasaland Digital | OpenAI |
|-----------------|-------------------|--------|
| **Control de Iteraciones** | ✅ (max_iterations=3) | ❌ |
| **Rate Limiting de Calls** | ⏳ Pendiente | ✅ (API) |
| **Validación de Outputs** | ⏳ Pendiente | ❌ |
| **Aislamiento de Contextos** | ⏳ Pendiente | ❌ |
| **Timeout por Workflow** | ⏳ Pendiente | ❌ |

#### Controles Actuales
- ✅ Límite de 3 iteraciones (previene loops infinitos)
- ✅ Estados persistentes en checkpointer (puede reanudar)
- ❌ **FALTA**: Timeout global por workflow (5 min)
- ❌ **FALTA**: Validación de outputs antes de almacenar
- ❌ **FALTA**: Aislamiento de contexto entre clientes

---

### 5. Workflow RFP Approval (Aprobación con HITL)

**Tipo**: Agente LangGraph con Human-in-the-Loop  
**Riesgo**: 🟡 **MEDIO**  
**Estado**: ✅ Activo

#### Descripción
Pipeline que pausa para revisión humana antes de aprobar propuestas generadas.

#### Componentes Técnicos

| Componente | Tecnología | Responsable |
|------------|------------|-------------|
| **Orquestador** | LangGraph (interrupt) | Brasaland Digital |
| **UI Aprobación** | React (Frontend) | Brasaland Digital |
| **Persistencia** | PostgreSQL (Checkpointer) | Brasaland Digital |

#### Archivos Clave
- `data/pipelines/rfp_approval/graph.py` (Grafo con interrupt)

#### Nodos del Workflow
1. **Prepare for Review**: Carga propuesta generada
2. **[INTERRUPT]**: Pausa para revisión humana
3. **Apply Human Feedback**: Incorpora cambios solicitados
4. **Finalize Approval**: Marca como aprobada

#### Datos Procesados
- ✅ Propuestas generadas (pendientes de aprobación)
- ✅ Feedback de revisores humanos

#### Superficie de Ataque
1. **Bypass de Aprobación**: Adversario manipula checkpointer para saltarse HITL
2. **Estado Corrupto**: Checkpointer es modificado directamente en DB
3. **Race Condition**: Dos usuarios intentan aprobar simultáneamente

#### Matriz de Responsabilidad Compartida

| Responsabilidad | Brasaland Digital |
|-----------------|-------------------|
| **Integridad de Checkpointer** | ✅ |
| **Control de Acceso a Aprobación** | ⏳ Pendiente (RBAC) |
| **Auditoría de Aprobaciones** | ⏳ Pendiente |
| **Prevención de Race Conditions** | ⏳ Pendiente (locks) |

#### Controles Actuales
- ✅ Interrupt obligatorio antes de acciones críticas
- ✅ Persistencia de estado en PostgreSQL
- ❌ **FALTA**: RBAC (solo gerentes pueden aprobar)
- ❌ **FALTA**: Auditoría de quién aprobó y cuándo
- ❌ **FALTA**: Locks de base de datos (optimistic locking)

---

### 6. Workflow Business Performance (Análisis de Métricas)

**Tipo**: Agente Analítico (No-LLM)  
**Riesgo**: 🟢 **BAJO**  
**Estado**: ✅ Activo

#### Descripción
Pipeline que analiza métricas de ventas, inventario y operaciones para generar reportes automáticos.

#### Componentes Técnicos

| Componente | Tecnología | Responsable |
|------------|------------|-------------|
| **Agregación Datos** | Pandas + SQL | Brasaland Digital |
| **Visualización** | Matplotlib / Plotly | Brasaland Digital |
| **Scheduler** | APScheduler | Brasaland Digital |

#### Archivos Clave
- `data/pipelines/business-performance/pipeline.py` (v1)
- `data/pipelines/business-performance/pipeline_v2.py` (v2 refactorizada)

#### Datos Procesados
- ✅ Ventas por local (agregadas)
- ✅ Inventario (stock)
- ✅ Métricas operacionales
- ❌ NO procesa datos personales

#### Superficie de Ataque
1. **SQL Injection**: Parámetros de queries no sanitizados (si aplica)
2. **Data Leakage**: Reportes exponen información sensible sin control de acceso

#### Controles Actuales
- ✅ Queries parametrizadas (protección contra SQL injection)
- ✅ Datos agregados (no individuales)
- ❌ **FALTA**: Control de acceso a reportes (quién puede ver qué)

---

### 7. Agent Memory Manager (Memoria Conversacional)

**Tipo**: Sistema de Memoria de Largo Plazo  
**Riesgo**: 🟡 **MEDIO**  
**Estado**: ✅ Activo

#### Descripción
Sistema que almacena memoria de conversaciones previas para agentes conversacionales (asistente ejecutivo de Mariana).

#### Componentes Técnicos

| Componente | Tecnología | Responsable |
|------------|------------|-------------|
| **Embeddings** | OpenAI text-embedding-3-small | OpenAI (Tercero) |
| **Almacenamiento** | Qdrant (colección separada) | Brasaland Digital |
| **Orquestador** | LangGraph | Brasaland Digital |

#### Archivos Clave
- `services/agent/memory/memory_manager.py`
- `services/agent/graph.py`

#### Datos Procesados
- ✅ Historial de conversaciones con Mariana (CEO)
- ⚠️ **RIESGO**: Podría contener información estratégica confidencial

#### Superficie de Ataque
1. **Context Poisoning**: Memoria manipulada para inyectar información falsa
2. **Cross-User Leakage**: Memoria de un usuario es accesible por otro
3. **PII in Memory**: Datos sensibles almacenados sin cifrar

#### Controles Actuales
- ✅ Colección Qdrant separada por usuario
- ✅ API Key en variables de entorno
- ❌ **FALTA**: Cifrado de memoria en reposo
- ❌ **FALTA**: TTL (Time-to-Live) para expirar memoria antigua
- ❌ **FALTA**: Aislamiento estricto (verificación de user_id)

---

### 8. Chat WebSocket con Token Streaming

**Tipo**: Sistema de Chat Bidireccional  
**Riesgo**: 🟡 **MEDIO**  
**Estado**: ✅ Activo (documentado)

#### Descripción
Sistema de chat en tiempo real con streaming de tokens desde LLM y funcionalidad de abort.

#### Componentes Técnicos

| Componente | Tecnología | Responsable |
|------------|------------|-------------|
| **Backend WebSocket** | FastAPI WebSocket | Brasaland Digital |
| **Frontend Hook** | React (useChatWebSocket) | Brasaland Digital |
| **Pub/Sub** | asyncio.Queue | Brasaland Digital |

#### Archivos Clave
- `services/routers/chat_ws.py` (Backend)
- `uis/backoffice/hooks/useChatWebSocket.ts` (Frontend)

#### Datos Procesados
- ✅ Mensajes de chat entre usuario y agente
- ✅ Historial de sesión

#### Superficie de Ataque
1. **WebSocket Hijacking**: Token JWT interceptado
2. **Message Injection**: Usuario envía mensajes maliciosos
3. **DoS via Abort**: Usuario aborta generaciones continuamente

#### Controles Actuales
- ✅ Autenticación JWT en handshake
- ✅ Abort genuino (asyncio.Task.cancel)
- ❌ **FALTA**: Re-validación periódica de JWT durante sesión
- ❌ **FALTA**: Rate limiting en mensajes por sesión

---

## 📊 Matriz Consolidada de Responsabilidad Compartida

| Responsabilidad | Brasaland | OpenAI | Anthropic | Qdrant |
|-----------------|-----------|--------|-----------|--------|
| **Disponibilidad del Servicio** | ⚠️ Parcial | ✅ | ✅ | ✅ |
| **Seguridad del Modelo** | ❌ | ✅ | ✅ | N/A |
| **Validación de Inputs** | ✅ | ❌ | ❌ | ❌ |
| **Sanitización de Outputs** | ✅ | ❌ | ❌ | ❌ |
| **Rate Limiting Aplicación** | ✅ | ⚠️ (API) | ⚠️ (API) | ❌ |
| **Logging y Auditoría** | ✅ | ❌ | ❌ | ❌ |
| **Cifrado en Tránsito** | ✅ | ✅ | ✅ | ✅ |
| **Cifrado en Reposo** | ⏳ Pendiente | ✅ | ✅ | ⏳ Pendiente |
| **Gestión de Incidentes** | ✅ | ✅ | ✅ | ✅ |
| **Compliance (GDPR/CCPA)** | ✅ | ✅ | ✅ | ⚠️ Parcial |

**Leyenda**:
- ✅ Responsabilidad completa
- ⚠️ Responsabilidad parcial o compartida
- ⏳ Pendiente de implementar
- ❌ No responsable

---

## 🚨 Plazos de Notificación de Incidentes

### Definición de Incidente de Seguridad de IA

Se considera **incidente de seguridad de IA** cualquiera de los siguientes eventos:

1. **Fuga de Datos Personales**:
   - Exposición de nombres, emails, teléfonos de empleados o clientes
   - Revelación de información del ATS (CVs, notas de entrevistas)

2. **Abuso del Sistema**:
   - Uso no autorizado de tools MCP
   - Creación masiva de incidencias falsas
   - Exfiltración de información confidencial vía prompt injection

3. **Compromiso de Credenciales**:
   - API keys filtradas o comprometidas
   - Tokens OAuth robados

4. **Fallo de Disponibilidad**:
   - Servicio de IA caído >4 horas
   - Bucle infinito que consume presupuesto completo de API

### Procedimiento de Notificación

#### Colombia (Ley 1581 - Habeas Data)

**Plazo**: **INMEDIATO**  
**Autoridad**: Superintendencia de Industria y Comercio (SIC)  
**Contacto**: protecciondedatos@sic.gov.co

**Procedimiento**:
1. Detectar incidente (tiempo T0)
2. Notificar a Tech Lead y Compliance Officer (T0 + 1 hora)
3. Evaluar alcance y afectados (T0 + 2 horas)
4. Notificar a SIC vía correo oficial (T0 + 4 horas)
5. Notificar a afectados (T0 + 24 horas)

**Plantilla de Notificación SIC**:
```
Asunto: Notificación de Incidente de Seguridad - Brasaland S.A.S.

Superintendencia de Industria y Comercio
Delegatura para la Protección de Datos Personales

Por medio de la presente, Brasaland S.A.S. (NIT: XXXXX) notifica un incidente de seguridad:

- Fecha del incidente: [YYYY-MM-DD HH:MM]
- Tipo de incidente: [Fuga de datos / Acceso no autorizado / Otro]
- Sistemas afectados: [Sistema de IA específico]
- Número de titulares afectados: [Estimación]
- Datos comprometidos: [Categorías de datos]
- Medidas de contención: [Acciones tomadas]
- Responsable: [Nombre + cargo]

Cordialmente,
[Firma Digital]
```

---

#### Florida (FIPA - FS § 501.171)

**Plazo**: **30 DÍAS**  
**Autoridad**: Florida Attorney General  
**Contacto**: https://www.myfloridalegal.com/

**Procedimiento**:
1. Detectar incidente (tiempo T0)
2. Notificar a Tech Lead y Compliance Officer (T0 + 1 hora)
3. Evaluar alcance (T0 + 5 días)
4. Notificar a afectados (T0 + 15 días)
5. Notificar a Florida AG (T0 + 30 días máximo)

**Criterio**: Solo si afecta a **500+ personas** en Florida

---

## 🔐 Roles y Responsabilidades

### Matriz RACI

| Actividad | Tech Lead | Compliance | DevOps | Data Scientist |
|-----------|-----------|------------|--------|----------------|
| **Diseño de Sistemas de IA** | A/R | C | I | R |
| **Implementación de Controles** | A | C | R | I |
| **Auditoría de Seguridad** | A | R | C | I |
| **Respuesta a Incidentes** | A | R | R | C |
| **Notificación a Autoridades** | A | R | I | I |
| **Revisión de Modelos** | A | C | I | R |
| **Gestión de Credenciales** | A | C | R | I |
| **Logging y Monitoreo** | A | C | R | I |

**Leyenda**:
- **R**: Responsible (ejecuta)
- **A**: Accountable (aprueba)
- **C**: Consulted (opina)
- **I**: Informed (informado)

### Contactos de Emergencia

| Rol | Nombre | Email | Teléfono |
|-----|--------|-------|----------|
| **Tech Lead** | Nicolás Park | nicolas.park@brasaland.com | +57 XXX XXX XXXX |
| **Compliance Officer** | [Asignar] | compliance@brasaland.com | +57 XXX XXX XXXX |
| **CEO** | Mariana Restrepo | mariana.restrepo@brasaland.com | +57 XXX XXX XXXX |

---

## 📅 Ciclo de Revisión

**Frecuencia**: **Trimestral** (cada 3 meses)

**Próximas Revisiones**:
- 2027-01-31
- 2027-04-30
- 2027-07-31
- 2027-10-31

**Triggers para Revisión Extraordinaria**:
1. Nuevo componente de IA implementado
2. Cambio de proveedor LLM (OpenAI → Anthropic)
3. Expansión a nueva jurisdicción (ej. California)
4. Incidente de seguridad mayor
5. Cambio en regulaciones (nueva ley de IA)

---

**Firmado**: Tech Lead Brasaland Digital  
**Fecha**: 2026-10-31  
**Versión**: 1.0

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
