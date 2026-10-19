# Project Brief - Brasaland Digital Platform

## Negocio

**Brasaland** es una cadena de restaurantes de cocina a la brasa fundada en 2008 en Medellín, Colombia. Opera **14 restaurantes propios** en dos países:
- **Colombia**: 10 locales (Medellín, Bogotá, Cali, Cartagena, Barranquilla)
- **Florida, USA**: 4 locales (Miami Beach, Miami Downtown, Orlando, Tampa)

**Métricas clave:**
- 115 empleados
- $6M USD facturación anual
- Alta rotación en personal de cocina
- 60% de clientes no usa programa de fidelización físico

**CEO**: Mariana Restrepo (hija del fundador, CEO desde 2019)  
**CTO**: Nicolás Park (Medellín)

## Valores de Marca

1. **Consistencia**: La comida sabe igual en Medellín o Miami
2. **Experiencia cálida**: Servicio consistente y amigable
3. **Velocidad**: Cocina rápida y eficiente

## Problema Central

Brasaland gestiona una **operación multicountry con herramientas de un solo restaurante**:
- Pedidos de materia prima por WhatsApp sin datos de inventario
- Sin visibilidad en tiempo real de los 14 locales
- Programa de fidelización con tarjetas físicas (60% no las usa)
- Decisiones basadas en llamadas e informes PDF semanales
- Sin CRM ni datos de clientes
- Competidores más pequeños ganan terreno con herramientas digitales

## Equipo Brasaland Digital

Equipo interno creado por Mariana para modernizar la operación:
- **Mandato**: Construir herramientas, sistemas y automatizaciones que permitan operar como empresa moderna sin perder el alma de la marca

## Áreas y Necesidades

### 🍖 Operaciones (Felipe Guerrero)
- Dashboard de ventas en tiempo real por local (COP/USD)
- Sistema inteligente de pedidos basado en históricos
- Alertas cuando un local no registra ventas

### 🛒 Compras (Lucía Fernández)
- ~20 proveedores entre Colombia y Florida
- Plataforma de gestión con historial de precios
- Visibilidad consolidada para negociación centralizada

### 📱 Marketing (Camila Ospina)
- Web de 2019 sin pedidos online
- App con 2.8 estrellas
- App digital de fidelización y pedidos
- CRM con historial y preferencias
- Motor de personalización

### 🧑‍🤝‍🧑 RRHH (Ashley Turner, Miami)
- 115 personas en 14 locales, 2 legislaciones laborales
- Portal interno (vacaciones, ausencias)
- Onboarding automatizado
- Dashboard KPIs (rotación, absentismo, cobertura)

### 🎓 Formación (Jake Morrison, Miami)
- Recetas y procedimientos en Google Drive desorganizado
- Plataforma de formación con catálogo searchable
- Onboarding estructurado
- Distribución simultánea de actualizaciones (ES/EN)

### 💻 Tecnología (Nicolás Park)
- Stack actual: web estática, app obsoleta, POS diferentes por país
- API central (locales, menús, ventas, clientes, proveedores)
- Telemetría en tiempo real
- Pipeline de datos para dashboards

### 📊 Dirección (Mariana Restrepo)
- Dashboard ejecutivo (ventas USD/COP)
- Asistente IA con queries en lenguaje natural
- Informe semanal automatizado (lunes 7am)

## Proyectos Implementados

### ✅ ATS (Applicant Tracking System)
**Objetivo**: Sistema de gestión de candidaturas para el área de RRHH
**Usuario**: Ashley Turner (Personas y Cultura)
**Problema resuelto**: Reducir tiempo de contratación y automatizar seguimiento de candidatos
**Estado**: ✅ 100% completado (14/14 criterios aprobados)

**Funcionalidades**:
- CRUD completo de candidatos
- Filtros por estado y etapa del proceso
- Búsqueda reactiva por nombre/email
- Gestión de notas por candidato
- Actualización de estado/etapa con PATCH
- Soporte multicountry (CO/US)
- Puestos específicos: Cocinero, Mesero, Cajero, Supervisor, Gerente

### ✅ Sistema de Análisis de Incidencias Postventa
**Objetivo**: Validar y analizar incidencias de los 14 locales para mejorar experiencia del cliente
**Usuario**: Operaciones + Dirección
**Problema resuelto**: Detectar patrones de problemas (calidad, servicio, infraestructura) para tomar acciones correctivas
**Estado**: ✅ 100% completado (3/3 fases: CLI, API, Frontend)

**Funcionalidades**:
- Validación de CSV contra especificaciones del negocio
- 6 categorías de incidencias (calidad_comida, servicio_cliente, operaciones, infraestructura, pedidos_online, facturacion)
- 4 estados (abierto, en_proceso, cerrado, descartado)
- 14 locales (10 CO + 4 US)
- Índice de satisfacción (1-5) para casos cerrados
- Métricas por categoría, estado y país
- Detección de registros inválidos con razón específica
- Exportación a CSV

## Próximos Proyectos Priorizados

1. **Dashboard Ejecutivo** (Mariana)
2. **App de Fidelización Digital** (Camila)
3. **Sistema de Pedidos Inteligente** (Felipe)
4. **Plataforma de Formación** (Jake)
5. **Portal RRHH** (Ashley)

## Principios de Desarrollo

1. **Contexto multicountry**: Siempre considerar Colombia vs Florida (moneda, legislación, idioma)
2. **Datos reales**: Usar locales reales, puestos reales, categorías del negocio
3. **Simplicidad**: Herramientas que el equipo pueda usar sin formación técnica
4. **Escalabilidad**: Preparado para crecer a más locales
5. **Marca Brasaland**: Paleta amber/orange, terminología en español

## Restricciones

- Sin herramientas externas de pago en fase MVP
- Datos de clientes son PII (Privacy Information), manejar con cuidado
- Cumplir legislación laboral de 2 países diferentes
- Mantener consistencia de marca en 2 mercados culturalmente distintos
