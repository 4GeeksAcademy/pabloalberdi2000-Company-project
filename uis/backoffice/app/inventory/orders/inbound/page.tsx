/**
 * Página: Registrar Entrada de Stock
 * Ruta: /inventory/orders/inbound
 * 
 * FUNCIONALIDAD:
 * - Formulario para registrar llegada de materia prima
 * - Selector de producto por NOMBRE (no IDs manuales)
 * - Confirmación visual tras envío exitoso
 * - Mensajes de error inline
 * 
 * EFECTO: Incrementa el stock disponible
 * PROTECCIÓN: Requiere autenticación JWT
 */

'use client';

import { useEffect, useState } from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import {
  getIngredients,
  createInboundOrder,
  type Ingredient,
  type InboundOrderCreateData,
  type WarehouseLocation,
  WAREHOUSE_LABELS,
  UNIT_LABELS,
} from '@/lib/inventory';

export default function InboundOrderPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedIngredient = searchParams.get('ingredient');

  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form state
  const [formData, setFormData] = useState<InboundOrderCreateData>({
    ingredient_id: preselectedIngredient ? parseInt(preselectedIngredient) : 0,
    quantity: 0,
    warehouse: '' as WarehouseLocation,
    notes: '',
  });

  // Cargar ingredientes
  useEffect(() => {
    if (!isAuthenticated) return;

    async function loadIngredients() {
      try {
        const data = await getIngredients();
        setIngredients(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error al cargar ingredientes');
      } finally {
        setLoading(false);
      }
    }

    loadIngredients();
  }, [isAuthenticated]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    // Validaciones
    if (!formData.ingredient_id || formData.ingredient_id === 0) {
      setError('Por favor selecciona un ingrediente');
      return;
    }

    if (formData.quantity <= 0) {
      setError('La cantidad debe ser mayor a 0');
      return;
    }

    if (!formData.warehouse) {
      setError('Por favor selecciona un almacén');
      return;
    }

    try {
      setSubmitting(true);
      await createInboundOrder(formData);

      // Éxito - limpiar formulario y mostrar confirmación
      setSuccess(true);
      setFormData({
        ingredient_id: 0,
        quantity: 0,
        warehouse: '' as WarehouseLocation,
        notes: '',
      });

      // Auto-ocultar mensaje de éxito después de 5 segundos
      setTimeout(() => setSuccess(false), 5000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al registrar entrada');
    } finally {
      setSubmitting(false);
    }
  };

  const selectedIngredient = ingredients.find(
    (ing) => ing.id === formData.ingredient_id
  );

  if (authLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="text-gray-600">Verificando autenticación...</div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/inventory/ingredients"
          className="text-amber-600 hover:text-amber-700 text-sm font-medium"
        >
          ← Volver al inventario
        </Link>
        <h1 className="text-3xl font-bold text-gray-900 mt-2">
          ➕ Registrar Entrada de Stock
        </h1>
        <p className="mt-2 text-gray-600">
          Registra la llegada de materia prima al almacén
        </p>
      </div>

      {/* Mensaje de éxito */}
      {success && (
        <div className="mb-6 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
          <strong className="font-semibold">✅ Entrada registrada exitosamente</strong>
          <p className="text-sm mt-1">El stock ha sido actualizado.</p>
        </div>
      )}

      {/* Mensaje de error */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <strong className="font-semibold">Error:</strong> {error}
        </div>
      )}

      {/* Formulario */}
      <form onSubmit={handleSubmit} className="bg-white shadow rounded-lg p-6">
        {/* Selector de ingrediente */}
        <div className="mb-6">
          <label htmlFor="ingredient" className="block text-sm font-medium text-gray-700 mb-1">
            Ingrediente *
          </label>
          <select
            id="ingredient"
            value={formData.ingredient_id}
            onChange={(e) =>
              setFormData({ ...formData, ingredient_id: parseInt(e.target.value) })
            }
            required
            disabled={loading}
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500"
          >
            <option value={0}>Seleccionar ingrediente...</option>
            {ingredients.map((ing) => (
              <option key={ing.id} value={ing.id}>
                {ing.name} ({ing.sku}) - Stock actual: {ing.current_stock.toFixed(2)} {UNIT_LABELS[ing.unit]}
              </option>
            ))}
          </select>
        </div>

        {/* Cantidad */}
        <div className="mb-6">
          <label htmlFor="quantity" className="block text-sm font-medium text-gray-700 mb-1">
            Cantidad *
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              id="quantity"
              step="0.01"
              min="0.01"
              value={formData.quantity || ''}
              onChange={(e) =>
                setFormData({ ...formData, quantity: parseFloat(e.target.value) || 0 })
              }
              required
              className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500"
              placeholder="0.00"
            />
            {selectedIngredient && (
              <span className="text-sm text-gray-600">
                {UNIT_LABELS[selectedIngredient.unit]}
              </span>
            )}
          </div>
        </div>

        {/* Almacén */}
        <div className="mb-6">
          <label htmlFor="warehouse" className="block text-sm font-medium text-gray-700 mb-1">
            Almacén de destino *
          </label>
          <select
            id="warehouse"
            value={formData.warehouse}
            onChange={(e) =>
              setFormData({ ...formData, warehouse: e.target.value as WarehouseLocation })
            }
            required
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500"
          >
            <option value="">Seleccionar almacén...</option>
            {Object.entries(WAREHOUSE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {/* Notas */}
        <div className="mb-6">
          <label htmlFor="notes" className="block text-sm font-medium text-gray-700 mb-1">
            Notas (opcional)
          </label>
          <textarea
            id="notes"
            value={formData.notes}
            onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
            rows={3}
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500"
            placeholder="Ej: Proveedor principal - Carne Argentina Premium"
          />
        </div>

        {/* Botones */}
        <div className="flex gap-3">
          <button
            type="submit"
            disabled={submitting}
            className="flex-1 bg-green-600 text-white px-6 py-3 rounded-md font-medium hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'Registrando...' : '✅ Registrar Entrada'}
          </button>
          <Link
            href="/inventory/ingredients"
            className="px-6 py-3 border border-gray-300 rounded-md font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            Cancelar
          </Link>
        </div>
      </form>

      {/* Info adicional */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">ℹ️ Información</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Las entradas incrementan el stock disponible del ingrediente</li>
          <li>• El stock actual se calcula automáticamente: Entradas - Salidas</li>
          <li>• Tu usuario será registrado como responsable de esta entrada</li>
        </ul>
      </div>
    </div>
  );
}
