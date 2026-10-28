/**
 * Página: Listado de Ingredientes
 * Ruta: /inventory/ingredients
 * 
 * FUNCIONALIDAD:
 * - Lista todos los ingredientes con stock calculado
 * - Semáforo visual de stock (crítico/bajo/saludable)
 * - Enlaces rápidos para registrar entradas/salidas
 * - Filtro por almacén
 * 
 * PROTECCIÓN: Requiere autenticación JWT
 */

'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import {
  getIngredients,
  type Ingredient,
  type WarehouseLocation,
  UNIT_LABELS,
  WAREHOUSE_LABELS,
  getStockLevel,
  STOCK_LEVEL_COLORS,
  STOCK_LEVEL_ICONS,
} from '@/lib/inventory';

export default function IngredientsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedWarehouse, setSelectedWarehouse] = useState<WarehouseLocation | ''>('');

  useEffect(() => {
    if (!isAuthenticated) return;

    async function loadIngredients() {
      try {
        setLoading(true);
        setError(null);
        const data = await getIngredients(
          selectedWarehouse ? { warehouse: selectedWarehouse } : undefined
        );
        setIngredients(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error al cargar ingredientes');
      } finally {
        setLoading(false);
      }
    }

    loadIngredients();
  }, [isAuthenticated, selectedWarehouse]);

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
        <h1 className="text-3xl font-bold text-gray-900">🍖 Inventario de Ingredientes</h1>
        <p className="mt-2 text-gray-600">
          Gestión de materia prima para los 14 restaurantes Brasaland
        </p>
      </div>

      {/* Filtros */}
      <div className="mb-6 bg-white p-4 rounded-lg shadow">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px]">
            <label htmlFor="warehouse" className="block text-sm font-medium text-gray-700 mb-1">
              Filtrar por almacén
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
          <p className="mt-2 text-gray-600">Cargando ingredientes...</p>
        </div>
      )}

      {/* Lista de ingredientes */}
      {!loading && ingredients.length === 0 && (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <p className="text-gray-600">No hay ingredientes registrados</p>
        </div>
      )}

      {!loading && ingredients.length > 0 && (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Estado
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Ingrediente
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  SKU
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                  Stock Actual
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                  Mínimo
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">
                  Punto Reorden
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {ingredients.map((ingredient) => {
                const stockLevel = getStockLevel(ingredient);
                const stockColor = STOCK_LEVEL_COLORS[stockLevel];
                const stockIcon = STOCK_LEVEL_ICONS[stockLevel];

                return (
                  <tr key={ingredient.id} className="hover:bg-gray-50">
                    {/* Semáforo de stock */}
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${stockColor}`}>
                        {stockIcon} {stockLevel === 'critical' ? 'Crítico' : stockLevel === 'low' ? 'Bajo' : 'OK'}
                      </span>
                    </td>

                    {/* Nombre */}
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">{ingredient.name}</div>
                      {ingredient.description && (
                        <div className="text-sm text-gray-500">{ingredient.description}</div>
                      )}
                    </td>

                    {/* SKU */}
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="text-sm text-gray-900 font-mono">{ingredient.sku}</span>
                    </td>

                    {/* Stock actual */}
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <span className="text-sm font-bold text-gray-900">
                        {ingredient.current_stock.toFixed(2)}
                      </span>
                      <span className="text-xs text-gray-500 ml-1">
                        {UNIT_LABELS[ingredient.unit]}
                      </span>
                    </td>

                    {/* Mínimo */}
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <span className="text-sm text-gray-600">
                        {ingredient.min_stock.toFixed(2)}
                      </span>
                    </td>

                    {/* Punto reorden */}
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <span className="text-sm text-gray-600">
                        {ingredient.reorder_point?.toFixed(2) || '-'}
                      </span>
                    </td>

                    {/* Acciones */}
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm">
                      <Link
                        href={`/inventory/orders/inbound?ingredient=${ingredient.id}`}
                        className="text-green-600 hover:text-green-900 font-medium mr-3"
                      >
                        ➕ Entrada
                      </Link>
                      <Link
                        href={`/inventory/orders/outbound?ingredient=${ingredient.id}`}
                        className="text-red-600 hover:text-red-900 font-medium"
                      >
                        ➖ Salida
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Leyenda de semáforo */}
      {!loading && ingredients.length > 0 && (
        <div className="mt-4 text-sm text-gray-600">
          <strong>Umbrales de stock:</strong>
          <span className="ml-2">🔴 Crítico = Stock &lt; Mínimo</span>
          <span className="ml-3">🟡 Bajo = Stock &lt; Punto de Reorden</span>
          <span className="ml-3">🟢 Saludable = Stock ≥ Punto de Reorden</span>
        </div>
      )}
    </div>
  );
}
