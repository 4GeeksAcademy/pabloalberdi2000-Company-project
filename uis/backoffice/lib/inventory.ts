/**
 * Inventory API Client for Brasaland
 *
 * Capa centralizada de integración con los endpoints /inventory del backend.
 *
 * ARQUITECTURA:
 * - Inyección automática de JWT token desde localStorage
 * - Gestión explícita de errores HTTP (4xx, 5xx)
 * - Tipado estricto con TypeScript
 * - Nunca exponer payloads JSON crudos al usuario
 *
 * REGLAS DE NEGOCIO:
 * - Stock es CALCULADO (current_stock viene del backend)
 * - Stock NO puede ser negativo (backend valida)
 * - user_uuid se obtiene automáticamente del JWT
 */

import { getToken, removeToken } from './auth';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============ TYPES ============

export type MeasurementUnit = 'kg' | 'g' | 'l' | 'ml' | 'unit' | 'package';

export type WarehouseLocation =
  | 'medellin_centro' | 'medellin_poblado' | 'medellin_envigado'
  | 'bogota_zona_rosa' | 'bogota_usaquen' | 'bogota_suba'
  | 'cali_norte' | 'cali_sur'
  | 'cartagena_centro' | 'barranquilla_norte'
  | 'miami_beach' | 'miami_downtown'
  | 'orlando_international' | 'tampa_centro'
  | 'central_warehouse';

export interface Ingredient {
  id: number;
  name: string;
  sku: string;
  description: string | null;
  unit: MeasurementUnit;
  min_stock: number;
  reorder_point: number | null;
  created_at: string;
  updated_at: string;
  // ⚠️ CAMPO CALCULADO - NO es editable
  current_stock: number;
  stock_by_warehouse: Record<string, number> | null;
}

export interface IngredientCreateData {
  name: string;
  sku: string;
  description?: string;
  unit: MeasurementUnit;
  min_stock: number;
  reorder_point?: number;
}

export interface InboundOrder {
  id: number;
  ingredient_id: number;
  quantity: number;
  warehouse: WarehouseLocation;
  user_uuid: string;
  notes: string | null;
  created_at: string;
  ingredient_name: string | null;
  ingredient_sku: string | null;
}

export interface InboundOrderCreateData {
  ingredient_id: number;
  quantity: number;
  warehouse: WarehouseLocation;
  notes?: string;
}

export interface OutboundOrder {
  id: number;
  ingredient_id: number;
  quantity: number;
  warehouse: WarehouseLocation;
  user_uuid: string;
  reason: string | null;
  created_at: string;
  ingredient_name: string | null;
  ingredient_sku: string | null;
}

export interface OutboundOrderCreateData {
  ingredient_id: number;
  quantity: number;
  warehouse: WarehouseLocation;
  reason?: string;
}

export interface Order {
  id: number;
  type: 'inbound' | 'outbound';
  ingredient_id: number;
  ingredient_name: string;
  ingredient_sku: string;
  quantity: number;
  warehouse: WarehouseLocation;
  user_uuid: string;
  notes_or_reason: string | null;
  created_at: string;
}

export interface StockReportItem {
  ingredient_id: number;
  ingredient_name: string;
  ingredient_sku: string;
  unit: MeasurementUnit;
  current_stock: number;
  min_stock: number;
  reorder_point: number | null;
  needs_reorder: boolean;
  stock_by_warehouse: Record<string, number>;
}

export interface StockReport {
  total_ingredients: number;
  low_stock_count: number;
  items: StockReportItem[];
  generated_at: string;
}

export interface InventoryFilters {
  warehouse?: WarehouseLocation;
  skip?: number;
  limit?: number;
}

export interface OrderFilters {
  order_type?: 'inbound' | 'outbound';
  ingredient_id?: number;
  warehouse?: WarehouseLocation;
  skip?: number;
  limit?: number;
}

// ============ API CLIENT ============

/**
 * Generic fetch wrapper con inyección automática de JWT
 * Gestiona errores HTTP explícitamente
 */
async function fetchInventoryAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}/inventory${endpoint}`;

  // Inyectar Authorization header
  const token = getToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
    ...options?.headers,
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Handle 401 Unauthorized - Session expired
    if (response.status === 401) {
      removeToken();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
      throw new Error('Sesión expirada. Por favor, inicia sesión nuevamente.');
    }

    // Handle 4xx and 5xx errors
    if (!response.ok) {
      let errorMessage = `Error ${response.status}`;

      try {
        const error = await response.json();
        // Backend devuelve errores en formato { detail: "mensaje" }
        errorMessage = error.detail || error.message || errorMessage;
      } catch {
        // Si no hay JSON, usar statusText
        errorMessage = response.statusText || errorMessage;
      }

      throw new Error(errorMessage);
    }

    // Para respuestas 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Error de conexión con el servidor');
  }
}

// ============ INGREDIENTS API ============

/**
 * Listar todos los ingredientes con stock calculado
 * GET /inventory/ingredients
 */
export async function getIngredients(filters?: InventoryFilters): Promise<Ingredient[]> {
  const params = new URLSearchParams();

  if (filters?.warehouse) params.set('warehouse', filters.warehouse);
  if (filters?.skip !== undefined) params.set('skip', filters.skip.toString());
  if (filters?.limit !== undefined) params.set('limit', filters.limit.toString());

  const queryString = params.toString();
  const endpoint = queryString ? `/ingredients?${queryString}` : '/ingredients';

  return fetchInventoryAPI<Ingredient[]>(endpoint);
}

/**
 * Obtener un ingrediente específico por ID
 * GET /inventory/ingredients/{id}
 */
export async function getIngredient(id: number, warehouse?: WarehouseLocation): Promise<Ingredient> {
  const params = new URLSearchParams();
  if (warehouse) params.set('warehouse', warehouse);

  const queryString = params.toString();
  const endpoint = queryString ? `/ingredients/${id}?${queryString}` : `/ingredients/${id}`;

  return fetchInventoryAPI<Ingredient>(endpoint);
}

/**
 * Crear nuevo ingrediente
 * POST /inventory/ingredients
 * Stock inicial será 0 (se incrementa con inbound orders)
 */
export async function createIngredient(data: IngredientCreateData): Promise<Ingredient> {
  return fetchInventoryAPI<Ingredient>('/ingredients', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Actualizar ingrediente (NO afecta stock)
 * PUT /inventory/ingredients/{id}
 * IMPORTANTE: Stock NO es editable, solo metadatos
 */
export async function updateIngredient(
  id: number,
  data: Partial<IngredientCreateData>
): Promise<Ingredient> {
  return fetchInventoryAPI<Ingredient>(`/ingredients/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// ============ INBOUND ORDERS API ============

/**
 * Registrar entrada de stock (llegada de materia prima)
 * POST /inventory/orders/inbound
 *
 * Efecto: Incrementa stock disponible
 * user_uuid: Se obtiene automáticamente del JWT
 */
export async function createInboundOrder(data: InboundOrderCreateData): Promise<InboundOrder> {
  return fetchInventoryAPI<InboundOrder>('/orders/inbound', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ============ OUTBOUND ORDERS API ============

/**
 * Registrar salida de stock (uso en cocina, merma)
 * POST /inventory/orders/outbound
 *
 * CRÍTICO: Backend valida stock no negativo ANTES de persistir
 * Si stock insuficiente → HTTP 400 con mensaje descriptivo
 *
 * Efecto: Decrementa stock disponible
 * user_uuid: Se obtiene automáticamente del JWT
 */
export async function createOutboundOrder(data: OutboundOrderCreateData): Promise<OutboundOrder> {
  return fetchInventoryAPI<OutboundOrder>('/orders/outbound', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ============ ORDERS HISTORY API ============

/**
 * Listar todas las órdenes (inbound + outbound)
 * GET /inventory/orders
 *
 * Vista de solo lectura para historial
 */
export async function getOrders(filters?: OrderFilters): Promise<Order[]> {
  const params = new URLSearchParams();

  if (filters?.order_type) params.set('order_type', filters.order_type);
  if (filters?.ingredient_id) params.set('ingredient_id', filters.ingredient_id.toString());
  if (filters?.warehouse) params.set('warehouse', filters.warehouse);
  if (filters?.skip !== undefined) params.set('skip', filters.skip.toString());
  if (filters?.limit !== undefined) params.set('limit', filters.limit.toString());

  const queryString = params.toString();
  const endpoint = queryString ? `/orders?${queryString}` : '/orders';

  return fetchInventoryAPI<Order[]>(endpoint);
}

// ============ STOCK REPORT API ============

/**
 * Obtener reporte completo de stock
 * GET /inventory/stock-report
 *
 * Incluye:
 * - Total de ingredientes
 * - Ingredientes con stock bajo
 * - Stock por almacén
 * - Indicadores de reorden
 */
export async function getStockReport(lowStockOnly: boolean = false): Promise<StockReport> {
  const params = new URLSearchParams();
  if (lowStockOnly) params.set('low_stock_only', 'true');

  const queryString = params.toString();
  const endpoint = queryString ? `/stock-report?${queryString}` : '/stock-report';

  return fetchInventoryAPI<StockReport>(endpoint);
}

// ============ HELPER FUNCTIONS ============

/**
 * Labels en español para unidades de medida
 */
export const UNIT_LABELS: Record<MeasurementUnit, string> = {
  kg: 'Kilogramos',
  g: 'Gramos',
  l: 'Litros',
  ml: 'Mililitros',
  unit: 'Unidades',
  package: 'Paquetes',
};

/**
 * Labels en español para almacenes/sedes
 */
export const WAREHOUSE_LABELS: Record<WarehouseLocation, string> = {
  medellin_centro: 'Medellín Centro',
  medellin_poblado: 'Medellín El Poblado',
  medellin_envigado: 'Medellín Envigado',
  bogota_zona_rosa: 'Bogotá Zona Rosa',
  bogota_usaquen: 'Bogotá Usaquén',
  bogota_suba: 'Bogotá Suba',
  cali_norte: 'Cali Norte',
  cali_sur: 'Cali Sur',
  cartagena_centro: 'Cartagena Centro',
  barranquilla_norte: 'Barranquilla Norte',
  miami_beach: 'Miami Beach',
  miami_downtown: 'Miami Downtown',
  orlando_international: 'Orlando International',
  tampa_centro: 'Tampa Centro',
  central_warehouse: 'Almacén Central',
};

/**
 * Determinar nivel de stock (para semáforo visual)
 *
 * Umbrales:
 * - CRITICAL: stock < min_stock
 * - LOW: stock < reorder_point
 * - HEALTHY: stock >= reorder_point
 */
export function getStockLevel(ingredient: Ingredient | StockReportItem): 'critical' | 'low' | 'healthy' {
  const { current_stock, min_stock, reorder_point } = ingredient;

  if (current_stock < min_stock) {
    return 'critical';
  }

  if (reorder_point && current_stock < reorder_point) {
    return 'low';
  }

  return 'healthy';
}

/**
 * Colores para semáforo de stock (clases Tailwind)
 */
export const STOCK_LEVEL_COLORS = {
  critical: 'text-red-600 bg-red-50 border-red-200',
  low: 'text-amber-600 bg-amber-50 border-amber-200',
  healthy: 'text-green-600 bg-green-50 border-green-200',
};

/**
 * Iconos para semáforo de stock (emoji)
 */
export const STOCK_LEVEL_ICONS = {
  critical: '🔴',
  low: '🟡',
  healthy: '🟢',
};
