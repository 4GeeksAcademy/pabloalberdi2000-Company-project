/**
 * Telemetry - Inventory Domain Events
 *
 * Helpers específicos para tracking de eventos del dominio de inventario.
 * Eventos según especificación en event-schemas.json.
 */

import { track } from "./telemetry";

// ============================================================
// Inventory Events (Obligatorios según TELEMETRY_PLAN.md)
// ============================================================

/**
 * Track: Intento de edición directa de stock (RECHAZADO).
 *
 * Hipótesis: Si un usuario intenta editar stock directamente,
 * indica falta de formación o intento de fraude.
 *
 * Decisión: Disparar entrenamiento adicional si >3 rechazos en 7 días.
 *
 * @param ingredientId - ID del ingrediente
 * @param ingredientName - Nombre del ingrediente (contexto humano)
 * @param warehouse - Almacén donde se intentó modificar
 * @param attemptedQuantity - Cantidad que intentó establecer
 * @param currentStock - Stock actual calculado
 * @param userRole - Rol del usuario (admin, operator, viewer)
 */
export function trackDirectStockEditRejected(params: {
  ingredientId: number;
  ingredientName: string;
  warehouse: string;
  attemptedQuantity: number;
  currentStock: number;
  userRole: string;
}): void {
  track("direct_stock_edit_rejected", {
    ingredient_id: params.ingredientId,
    ingredient_name: params.ingredientName,
    warehouse: params.warehouse,
    attempted_quantity: params.attemptedQuantity,
    current_stock: params.currentStock,
    rejection_reason: "Direct stock edits not allowed. Use inbound/outbound orders.",
    user_role: params.userRole,
  });
}

/**
 * Track: Orden de salida rechazada por stock insuficiente.
 *
 * Hipótesis: Desajuste entre stock registrado y stock real físico.
 * Decisión: Enviar alerta al supervisor para auditoría física.
 *
 * @param ingredientId - ID del ingrediente
 * @param ingredientName - Nombre del ingrediente
 * @param warehouse - Almacén
 * @param requestedQuantity - Cantidad solicitada
 * @param availableStock - Stock disponible
 */
export function trackOutboundStockInsufficient(params: {
  ingredientId: number;
  ingredientName: string;
  warehouse: string;
  requestedQuantity: number;
  availableStock: number;
}): void {
  track("outbound_stock_insufficient", {
    ingredient_id: params.ingredientId,
    ingredient_name: params.ingredientName,
    warehouse: params.warehouse,
    requested_quantity: params.requestedQuantity,
    available_stock: params.availableStock,
    shortage_quantity: params.requestedQuantity - params.availableStock,
  });
}

/**
 * Track: Umbral de stock mínimo alcanzado.
 *
 * Hipótesis: Stock <min_stock indica riesgo de desabasto en 24-48h.
 * Decisión: Notificación push a Compras (Lucía Fernández) + orden automática.
 *
 * @param ingredientId - ID del ingrediente
 * @param ingredientName - Nombre del ingrediente
 * @param warehouse - Almacén
 * @param currentStock - Stock actual
 * @param minStock - Umbral mínimo configurado
 * @param reorderPoint - Punto de reorden
 * @param severity - Severidad (low, warning, critical)
 */
export function trackStockThresholdTriggered(params: {
  ingredientId: number;
  ingredientName: string;
  warehouse: string;
  currentStock: number;
  minStock: number;
  reorderPoint: number;
  severity: "low" | "warning" | "critical";
}): void {
  track("stock_threshold_triggered", {
    ingredient_id: params.ingredientId,
    ingredient_name: params.ingredientName,
    warehouse: params.warehouse,
    current_stock: params.currentStock,
    min_stock: params.minStock,
    reorder_point: params.reorderPoint,
    threshold_severity: params.severity,
  });
}

/**
 * Track: Visualización de ingrediente con stock crítico.
 *
 * Hipótesis: Medir efectividad de alertas (¿usuario responde en <24h?).
 * Decisión: Escalar a gerente si ingrediente crítico no atendido en 24h.
 *
 * Nota: Este evento tiene debouncing de 5s para evitar duplicados.
 *
 * @param ingredientId - ID del ingrediente
 * @param ingredientName - Nombre del ingrediente
 * @param warehouse - Almacén
 * @param currentStock - Stock actual
 */
export function trackIngredientViewedCriticalStock(params: {
  ingredientId: number;
  ingredientName: string;
  warehouse: string;
  currentStock: number;
}): void {
  // Debouncing en memoria (5 segundos)
  const key = `ingredient_viewed_${params.ingredientId}_${params.warehouse}`;
  const lastTrack = (globalThis as any).__telemetry_debounce?.[key] || 0;
  const now = Date.now();

  if (now - lastTrack < 5000) {
    return; // Skip: debounce activo
  }

  // Guardar timestamp de último track
  (globalThis as any).__telemetry_debounce = {
    ...((globalThis as any).__telemetry_debounce || {}),
    [key]: now,
  };

  track("ingredient_viewed_critical_stock", {
    ingredient_id: params.ingredientId,
    ingredient_name: params.ingredientName,
    warehouse: params.warehouse,
    current_stock: params.currentStock,
    viewed_at: new Date().toISOString(),
  });
}

/**
 * Track: Latencia de cálculo de stock.
 *
 * Hipótesis: Si cálculo tarda >500ms (p95), indica query N+1 o falta de índice.
 * Decisión: Alerta a tecnología si p95 >500ms durante 15 min.
 *
 * Nota: Sampling 25% según TELEMETRY_PLAN.md.
 *
 * @param ingredientId - ID del ingrediente
 * @param warehouse - Almacén
 * @param latencyMs - Tiempo de cálculo en ms
 */
export function trackStockCalculationLatency(params: {
  ingredientId: number;
  warehouse: string;
  latencyMs: number;
}): void {
  // Sampling 25%
  if (Math.random() > 0.25) return;

  track("stock_calculation_latency", {
    ingredient_id: params.ingredientId,
    warehouse: params.warehouse,
    latency_ms: params.latencyMs,
    threshold_exceeded: params.latencyMs > 500,
  });
}

/**
 * Track: Orden de entrada creada.
 *
 * Hipótesis: Patrones de órdenes alimentan predicción de demanda (ML).
 * Decisión: Modelo predictivo con 85%+ precisión en forecast 7 días.
 *
 * @param orderId - ID de la orden
 * @param ingredientId - ID del ingrediente
 * @param quantity - Cantidad ingresada
 * @param unit - Unidad de medida
 * @param warehouse - Almacén de destino
 */
export function trackInboundOrderCreated(params: {
  orderId: number;
  ingredientId: number;
  quantity: number;
  unit: string;
  warehouse: string;
}): void {
  track("inbound_order_created", {
    order_id: params.orderId,
    ingredient_id: params.ingredientId,
    quantity: params.quantity,
    unit: params.unit,
    warehouse: params.warehouse,
  });
}

/**
 * Track: Orden de salida creada.
 *
 * Hipótesis: Análisis de consumo por almacén permite optimizar inventario.
 * Decisión: Ajuste de min_stock por local según consumo histórico.
 *
 * @param orderId - ID de la orden
 * @param ingredientId - ID del ingrediente
 * @param quantity - Cantidad consumida
 * @param unit - Unidad de medida
 * @param warehouse - Almacén origen
 * @param reason - Razón del consumo
 */
export function trackOutboundOrderCreated(params: {
  orderId: number;
  ingredientId: number;
  quantity: number;
  unit: string;
  warehouse: string;
  reason: string;
}): void {
  track("outbound_order_created", {
    order_id: params.orderId,
    ingredient_id: params.ingredientId,
    quantity: params.quantity,
    unit: params.unit,
    warehouse: params.warehouse,
    reason: params.reason,
  });
}
