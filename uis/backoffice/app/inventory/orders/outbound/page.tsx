/**
 * Página: Registrar Salida de Stock
 * Ruta: /inventory/orders/outbound
 * 
 * FUNCIONALIDAD CRÍTICA:
 * - Consulta reactiva de stock al seleccionar producto + almacén
 * - Muestra stock disponible ANTES de que usuario ingrese cantidad
 * - Advertencia preventiva si cantidad > stock disponible
 * - Manejo de error HTTP 400 inline (stock insuficiente)
 * 
 * EFECTO: Decrementa el stock disponible
 * VALIDACIÓN: Backend rechaza si stock < cantidad
 * PROTECCIÓN: Requiere autenticación JWT
 */

'use client';

import { useEffect, useState } from 'next';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';
import {
  getIngredients,
  getIngredient,
  createOutboundOrder,
  type Ingredient,
  type OutboundOrderCreateData,
  type WarehouseLocation,
  WAREHOUSE_LABELS,
  UNIT_LABELS,
} from '@/lib/inventory';

export default function OutboundOrderPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedIngredient = searchParams.get('ingredient');

  const [ingredients, setIngredients] = useState<Ingredient[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [quantityError, setQuantityError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // ⚠️ ESTADO CRÍTICO: Stock disponible en almacén seleccionado
  const [availableStock, setAvailableStock] = useState<number | null>(null);
  const [checkingStock, setCheckingStock] = useState(false);

  // Form state
  const [formData, setFormData] = useState<OutboundOrderCreateData>({
    ingredient_id: preselectedIngredient ? parseInt(preselectedIngredient) : 0,
    quantity: 0,
    warehouse: '' as WarehouseLocation,
    reason: '',
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

  // ⚠️ LÓGICA CRÍTICA: Consultar stock disponible cuando cambia producto o almacén
  useEffect(() => {
    if (!formData.ingredient_id || formData.ingredient_id === 0 || !formData.warehouse) {
      setAvailableStock(null);
      setQuantityError(null);
      return;
    }

    async function checkStock() {
      try {
        setCheckingStock(true);
        const ingredient = await getIngredient(formData.ingredient_id, formData.warehouse);
        setAvailableStock(ingredient.current_stock);
        
        // Validar si la cantidad ingresada excede el stock
        if (formData.quantity > 0 && formData.quantity > ingredient.current_stock) {
          setQuantityError(
            `⚠️ Cantidad excede stock disponible. Disponible: ${ingredient.current_stock.toFixed(2)} ${UNIT_LABELS[ingredient.unit]}`
          );
        } else {
          setQuantityError(null);
        }
      } catch (err) {
        console.error('Error checking stock:', err);
        setAvailableStock(null);
      } finally {
        setCheckingStock(false);
      }
    }

    checkStock();
  }, [formData.ingredient_id, formData.warehouse, formData.quantity]);

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

    // Advertencia preventiva (no bloqueante)
    if (availableStock !== null && formData.quantity > availableStock) {
      const confirmed = confirm(
        `⚠️ ADVERTENCIA: La cantidad solicitada (${formData.quantity}) excede el stock disponible (${availableStock}).\n\n¿Deseas continuar de todas formas?\n\nNota: El servidor rechazará esta orden si el stock es insuficiente.`
      );
      if (!confirmed) return;
    }

    try {
      setSubmitting(true);
      await createOutboundOrder(formData);

      // Éxito - limpiar formulario y mostrar confirmación
      setSuccess(true);
      setFormData({
        ingredient_id: 0,
        quantity: 0,
        warehouse: '' as WarehouseLocation,
        reason: '',
      });
      setAvailableStock(null);
      setQuantityError(null);

      // Auto-ocultar mensaje de éxito después de 5 segundos
      setTimeout(() => setSuccess(false), 5000);
    } catch (err) {
      // ⚠️ Manejar error HTTP 400 de stock insuficiente
      const errorMessage = err instanceof Error ? err.message : 'Error al registrar salida';
      
      // Si es error de stock insuficiente, mostrarlo inline junto al campo
      if (errorMessage.toLowerCase().includes('insufficient stock')) {
        setQuantityError(`❌ ${errorMessage}`);
        setError(null);
      } else {
        setError(errorMessage);
        setQuantityError(null);
      }
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
          ➖ Registrar Salida de Stock
        </h1>
        <p className="mt-2 text-gray-600">
          Registra el uso de materia prima (cocina, merma, etc.)
        </p>
      </div>

      {/* Mensaje de éxito */}
      {success && (
        <div className="mb-6 bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
          <strong className="font-semibold">✅ Salida registrada exitosamente</strong>
          <p className="text-sm mt-1">El stock ha sido actualizado.</p>
        </div>
      )}

      {/* Mensaje de error general */}
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
                {ing.name} ({ing.sku})
              </option>
            ))}
          </select>
        </div>

        {/* Almacén */}
        <div className="mb-6">
          <label htmlFor="warehouse" className="block text-sm font-medium text-gray-700 mb-1">
            Almacén de origen *
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

        {/* ⚠️ DISPLAY REACTIVO: Stock disponible */}
        {formData.ingredient_id > 0 && formData.warehouse && (
          <div className={`mb-6 p-4 rounded-lg border ${
            checkingStock ? 'bg-gray-50 border-gray-200' :
            availableStock !== null && availableStock > 0 ? 'bg-green-50 border-green-200' :
            'bg-red-50 border-red-200'
          }`}>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Stock disponible:</span>
              {checkingStock ? (
                <span className="text-sm text-gray-600">Consultando...</span>
              ) : availableStock !== null ? (
                <span className={`text-lg font-bold ${
                  availableStock > 0 ? 'text-green-700' : 'text-red-700'
                }`}>
                  {availableStock.toFixed(2)} {selectedIngredient && UNIT_LABELS[selectedIngredient.unit]}
                </span>
              ) : (
                <span className="text-sm text-gray-600">Error al consultar</span>
              )}
            </div>
          </div>
        )}

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
              className={`flex-1 border rounded-md px-3 py-2 focus:outline-none focus:ring-2 ${
                quantityError
                  ? 'border-red-300 focus:ring-red-500'
                  : 'border-gray-300 focus:ring-amber-500'
              }`}
              placeholder="0.00"
            />
            {selectedIngredient && (
              <span className="text-sm text-gray-600">
                {UNIT_LABELS[selectedIngredient.unit]}
              </span>
            )}
          </div>
          
          {/* ⚠️ ERROR INLINE: Cantidad excede stock */}
          {quantityError && (
            <p className="mt-2 text-sm text-red-600 font-medium">{quantityError}</p>
          )}
        </div>

        {/* Motivo */}
        <div className="mb-6">
          <label htmlFor="reason" className="block text-sm font-medium text-gray-700 mb-1">
            Motivo (opcional)
          </label>
          <textarea
            id="reason"
            value={formData.reason}
            onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
            rows={3}
            className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-amber-500"
            placeholder="Ej: Uso en cocina - Servicio del día"
          />
        </div>

        {/* Botones */}
        <div className="flex gap-3">
          <button
            type="submit"
            disabled={submitting || checkingStock}
            className="flex-1 bg-red-600 text-white px-6 py-3 rounded-md font-medium hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'Registrando...' : '✅ Registrar Salida'}
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
      <div className="mt-6 bg-amber-50 border border-amber-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-amber-900 mb-2">⚠️ Importante</h3>
        <ul className="text-sm text-amber-800 space-y-1">
          <li>• Las salidas decrementan el stock disponible del ingrediente</li>
          <li>• El stock NO puede ser negativo (el sistema lo validará)</li>
          <li>• Si hay stock insuficiente, la operación será rechazada</li>
          <li>• Tu usuario será registrado como responsable de esta salida</li>
        </ul>
      </div>
    </div>
  );
}
