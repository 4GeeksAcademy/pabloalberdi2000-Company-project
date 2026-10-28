/**
 * Página: Historial de Órdenes
 * Ruta: /inventory/orders/history
 * 
 * FUNCIONALIDAD:
 * - Vista de SOLO LECTURA de todas las órdenes (inbound + outbound)
 * - Distinción visual clara entre entradas y salidas
 * - Filtros por tipo, ingrediente, almacén
 * - Muestra trazabilidad (user_uuid)
 * 
 * REGLA: Sin botones de edición o eliminación
 * PROTECCIÓN: Requiere autenticación JWT
 */

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import {
  getOrders,
  type Order,
  type WarehouseLocation,
  WAREHOUSE_LABELS,
} from '@/lib/inventory';

export default function OrdersHistoryPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filtros
  const [orderType, setOrderType] = useState<'inbound' | 'outbound' | ''>('');
  const [selectedWarehouse, setSelectedWarehouse] = useState<WarehouseLocation | ''>('');

  useEffect(() => {
    if (!isAuthenticated) return;

    async function loadOrders() {
      try {
        setLoading(true);
        setError(null);
        
        const filters: any = {};
        if (orderType) filters.order_type = orderType;
        if (selectedWarehouse) filters.warehouse = selectedWarehouse;

        const data = await getOrders(filters);
        setOrders(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error al cargar historial');
      } finally {
        setLoading(false);
      }
    }

    loadOrders();
  }, [isAuthenticated, orderType, selectedWarehouse]);

  if (authLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-gray-600">Verificando autenticación...</div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/inventory/ingredients"
          className="text-amber-600 hover:text-amber-700 text-sm font-medium"
        >
          ← Volver al inventario
        </Link>
        <h1 className="text-3xl font-bold text-gray-900 mt-2">📋 Historial de Órdenes</h1>
        <p className="mt-2 text-gray-600">
          Registro completo de entradas y salidas de stock
        </p>
      </div>

      {/* Filtros */}
      <div className="mb-6 bg-white p-4 rounded-lg shadow">
        <div className="flex flex-wrap gap-4">
          {/* Tipo de orden */}
          <div className="flex-1 min-w-[200px]">
            <label htmlFor="orderType" className="block text-sm font-medium text-gray-700 mb-1">
              Tipo de orden
            </label>
            <select
              id="orderType"
              value={orderType}
              onChange={(e) => setOrderType(e.target.value as any)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              <option value="">Todas las órdenes</option>
              <option value="inbound">Entradas</option>
              <option value="outbound">Salidas</option>
            </select>
          </div>

          {/* Almacén */}
          <div className="flex-1 min-w-[200px]">
            <label htmlFor="warehouse" className="block text-sm font-medium text-gray-700 mb-1">
              Almacén
            </label>
            <select
              id="warehouse"
              value={selectedWarehouse}
              onChange={(e) => setSelectedWarehouse(e.target.value as WarehouseLocation | '')}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500"
            >
              <option value="">Todos los almacenes</option>
              {Object.entries(WAREHOUSE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <strong className="font-semibold">Error:</strong> {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-amber-600"></div>
          <p className="mt-2 text-gray-600">Cargando historial...</p>
        </div>
      )}

      {/* Sin resultados */}
      {!loading && orders.length === 0 && (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-600">No hay órdenes registradas</p>
        </div>
      )}

      {/* Lista de órdenes */}
      {!loading && orders.length > 0 && (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Tipo
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Ingrediente
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  SKU
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                  Cantidad
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Almacén
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Usuario
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Fecha
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Notas / Motivo
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {orders.map((order) => (
                <tr key={`${order.type}-${order.id}`} className="hover:bg-gray-50">
                  {/* Tipo con badge coloreado */}
                  <td className="px-6 py-4 whitespace-nowrap">
                    {order.type === 'inbound' ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 border border-green-200">
                        ➕ Entrada
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 border border-red-200">
                        ➖ Salida
                      </span>
                    )}
                  </td>

                  {/* Ingrediente */}
                  <td className="px-6 py-4">
                    <div className="text-sm font-medium text-gray-900">
                      {order.ingredient_name}
                    </div>
                  </td>

                  {/* SKU */}
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-600 font-mono">
                      {order.ingredient_sku}
                    </span>
                  </td>

                  {/* Cantidad */}
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <span className={`text-sm font-semibold ${
                      order.type === 'inbound' ? 'text-green-700' : 'text-red-700'
                    }`}>
                      {order.type === 'inbound' ? '+' : '-'}{order.quantity.toFixed(2)}
                    </span>
                  </td>

                  {/* Almacén */}
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-900">
                      {WAREHOUSE_LABELS[order.warehouse]}
                    </span>
                  </td>

                  {/* Usuario (trazabilidad) */}
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-600 font-mono">
                      {order.user_uuid}
                    </span>
                  </td>

                  {/* Fecha */}
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-gray-600">
                      {new Date(order.created_at).toLocaleString('es-ES', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </td>

                  {/* Notas / Motivo */}
                  <td className="px-6 py-4">
                    <span className="text-sm text-gray-600">
                      {order.notes_or_reason || '-'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Estadísticas rápidas */}
      {!loading && orders.length > 0 && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded-lg shadow">
            <div className="text-sm text-gray-600">Total de órdenes</div>
            <div className="text-2xl font-bold text-gray-900">{orders.length}</div>
          </div>
          <div className="bg-green-50 p-4 rounded-lg shadow border border-green-200">
            <div className="text-sm text-green-700">Entradas</div>
            <div className="text-2xl font-bold text-green-900">
              {orders.filter(o => o.type === 'inbound').length}
            </div>
          </div>
          <div className="bg-red-50 p-4 rounded-lg shadow border border-red-200">
            <div className="text-sm text-red-700">Salidas</div>
            <div className="text-2xl font-bold text-red-900">
              {orders.filter(o => o.type === 'outbound').length}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
