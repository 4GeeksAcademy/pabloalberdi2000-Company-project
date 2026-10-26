'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import {
  createIncident,
  getIncidents,
  updateIncidentStatus,
  getIncidentsSummary,
  type Incident,
  type IncidentCreateData,
  type IncidentFilters,
  type IncidentSummary,
  type IncidentStatus,
  type IncidentOrigin,
  type IncidentCategory,
  type IncidentBranch,
} from '@/lib/api';

// ============================================================
// CONSTANTS FROM BRIEFING_INCIDENCIAS.md
// ============================================================

const CATEGORIES: { value: IncidentCategory; label: string; description: string }[] = [
  { value: 'calidad_comida', label: 'Calidad de Comida', description: 'Sabor, cocción, temperatura, presentación' },
  { value: 'servicio_cliente', label: 'Servicio al Cliente', description: 'Atención del personal, tiempos de espera' },
  { value: 'operaciones', label: 'Operaciones', description: 'Logística, stock, proveedores' },
  { value: 'infraestructura', label: 'Infraestructura', description: 'Equipos, instalaciones, limpieza' },
  { value: 'pedidos_online', label: 'Pedidos Online', description: 'Problemas con app o web' },
  { value: 'facturacion', label: 'Facturación', description: 'Errores en cuentas, cobros' },
];

const ORIGINS: { value: IncidentOrigin; label: string }[] = [
  { value: 'customer', label: 'Cliente' },
  { value: 'branch', label: 'Sede/Local' },
  { value: 'internal', label: 'Interno' },
];

const BRANCHES: { value: IncidentBranch; label: string; country: string }[] = [
  // Colombia
  { value: 'medellin_centro', label: 'Medellín Centro', country: 'CO' },
  { value: 'medellin_poblado', label: 'Medellín Poblado', country: 'CO' },
  { value: 'medellin_envigado', label: 'Medellín Envigado', country: 'CO' },
  { value: 'bogota_zona_rosa', label: 'Bogotá Zona Rosa', country: 'CO' },
  { value: 'bogota_usaquen', label: 'Bogotá Usaquén', country: 'CO' },
  { value: 'bogota_suba', label: 'Bogotá Suba', country: 'CO' },
  { value: 'cali_norte', label: 'Cali Norte', country: 'CO' },
  { value: 'cali_sur', label: 'Cali Sur', country: 'CO' },
  { value: 'cartagena_centro', label: 'Cartagena Centro', country: 'CO' },
  { value: 'barranquilla_norte', label: 'Barranquilla Norte', country: 'CO' },
  // Florida
  { value: 'miami_beach', label: 'Miami Beach', country: 'US' },
  { value: 'miami_downtown', label: 'Miami Downtown', country: 'US' },
  { value: 'orlando_international', label: 'Orlando International', country: 'US' },
  { value: 'tampa_centro', label: 'Tampa Centro', country: 'US' },
  // Central
  { value: 'central', label: 'Central (No específico de sede)', country: 'N/A' },
];

const STATUSES: { value: IncidentStatus; label: string; color: string }[] = [
  { value: 'open', label: 'Abierto', color: 'bg-red-100 text-red-800 border-red-200' },
  { value: 'in_progress', label: 'En Proceso', color: 'bg-yellow-100 text-yellow-800 border-yellow-200' },
  { value: 'resolved', label: 'Resuelto', color: 'bg-green-100 text-green-800 border-green-200' },
  { value: 'discarded', label: 'Descartado', color: 'bg-gray-100 text-gray-800 border-gray-200' },
];

// ============================================================
// MAIN COMPONENT
// ============================================================

export default function IncidentsManagerPage() {
  const router = useRouter();
  const { isAuthenticated, loading: authLoading } = useAuth();

  // Route protection
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  // View state
  const [activeTab, setActiveTab] = useState<'create' | 'list' | 'summary'>('list');

  if (authLoading) {
    return (
      <div className="container mx-auto flex min-h-screen items-center justify-center px-4">
        <div className="text-center">
          <div className="mb-4 inline-block h-12 w-12 animate-spin rounded-full border-4 border-orange-600 border-t-transparent"></div>
          <p className="text-amber-800">Cargando...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-amber-950">Gestor de Incidencias</h1>
        <p className="mt-2 text-amber-800">
          Registra, consulta y gestiona incidencias de los 14 locales de Brasaland
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex space-x-1 border-b border-amber-200">
        <button
          onClick={() => setActiveTab('list')}
          className={`px-6 py-3 font-semibold transition-colors ${
            activeTab === 'list'
              ? 'border-b-2 border-orange-600 text-orange-600'
              : 'text-amber-700 hover:text-amber-900'
          }`}
        >
          📋 Listado
        </button>
        <button
          onClick={() => setActiveTab('create')}
          className={`px-6 py-3 font-semibold transition-colors ${
            activeTab === 'create'
              ? 'border-b-2 border-orange-600 text-orange-600'
              : 'text-amber-700 hover:text-amber-900'
          }`}
        >
          ➕ Registrar Incidencia
        </button>
        <button
          onClick={() => setActiveTab('summary')}
          className={`px-6 py-3 font-semibold transition-colors ${
            activeTab === 'summary'
              ? 'border-b-2 border-orange-600 text-orange-600'
              : 'text-amber-700 hover:text-amber-900'
          }`}
        >
          📊 Métricas
        </button>
      </div>

      {/* Content */}
      {activeTab === 'create' && <CreateIncidentForm onSuccess={() => setActiveTab('list')} />}
      {activeTab === 'list' && <IncidentsList />}
      {activeTab === 'summary' && <IncidentsSummary />}
    </div>
  );
}

// ============================================================
// CREATE INCIDENT FORM
// ============================================================

function CreateIncidentForm({ onSuccess }: { onSuccess: () => void }) {
  const [formData, setFormData] = useState<IncidentCreateData>({
    title: '',
    description: '',
    category: 'calidad_comida',
    origin: 'customer',
    branch: 'central',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      await createIncident(formData);
      setSuccess(true);

      // Limpiar formulario
      setFormData({
        title: '',
        description: '',
        category: 'calidad_comida',
        origin: 'customer',
        branch: 'central',
      });

      // Auto-redirect después de 2 segundos
      setTimeout(() => {
        setSuccess(false);
        onSuccess();
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear la incidencia');
    } finally {
      setLoading(false);
    }
  };

  // Highlight branch when origin is "branch"
  const isBranchOrigin = formData.origin === 'branch';

  return (
    <div className="rounded-lg border border-amber-200 bg-white p-6 shadow-sm">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Title */}
        <div>
          <label htmlFor="title" className="mb-1 block text-sm font-medium text-amber-900">
            Título <span className="text-red-600">*</span>
          </label>
          <input
            id="title"
            type="text"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            required
            maxLength={255}
            className="w-full rounded-lg border border-amber-200 px-4 py-2 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500"
            placeholder="Resumen breve de la incidencia"
          />
        </div>

        {/* Description */}
        <div>
          <label htmlFor="description" className="mb-1 block text-sm font-medium text-amber-900">
            Descripción <span className="text-red-600">*</span>
          </label>
          <textarea
            id="description"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            required
            maxLength={2000}
            rows={4}
            className="w-full rounded-lg border border-amber-200 px-4 py-2 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500"
            placeholder="Descripción detallada del problema"
          />
        </div>

        {/* Category */}
        <div>
          <label htmlFor="category" className="mb-1 block text-sm font-medium text-amber-900">
            Categoría <span className="text-red-600">*</span>
          </label>
          <select
            id="category"
            value={formData.category}
            onChange={(e) => setFormData({ ...formData, category: e.target.value as IncidentCategory })}
            required
            className="w-full rounded-lg border border-amber-200 px-4 py-2 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500"
          >
            {CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label} - {cat.description}
              </option>
            ))}
          </select>
        </div>

        {/* Origin */}
        <div>
          <label htmlFor="origin" className="mb-1 block text-sm font-medium text-amber-900">
            Origen del Reporte <span className="text-red-600">*</span>
          </label>
          <select
            id="origin"
            value={formData.origin}
            onChange={(e) => setFormData({ ...formData, origin: e.target.value as IncidentOrigin })}
            required
            className="w-full rounded-lg border border-amber-200 px-4 py-2 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500"
          >
            {ORIGINS.map((origin) => (
              <option key={origin.value} value={origin.value}>
                {origin.label}
              </option>
            ))}
          </select>
        </div>

        {/* Branch - Highlighted when origin is "branch" */}
        <div className={isBranchOrigin ? 'rounded-lg border-2 border-orange-600 bg-orange-50 p-4' : ''}>
          <label htmlFor="branch" className="mb-1 block text-sm font-medium text-amber-900">
            Sede/Local <span className="text-red-600">*</span>
            {isBranchOrigin && (
              <span className="ml-2 text-xs font-semibold text-orange-600">
                ⚠️ Reportando desde sede
              </span>
            )}
          </label>
          <select
            id="branch"
            value={formData.branch}
            onChange={(e) => setFormData({ ...formData, branch: e.target.value as IncidentBranch })}
            required
            className={`w-full rounded-lg border px-4 py-2 focus:outline-none focus:ring-2 ${
              isBranchOrigin
                ? 'border-orange-400 bg-white focus:border-orange-500 focus:ring-orange-500'
                : 'border-amber-200 focus:border-orange-500 focus:ring-orange-500'
            }`}
          >
            {BRANCHES.map((branch) => (
              <option key={branch.value} value={branch.value}>
                {branch.label} {branch.country !== 'N/A' && `(${branch.country})`}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-amber-700">
            Selecciona "Central" si la incidencia no es específica de una sede
          </p>
        </div>

        {/* Success Message */}
        {success && (
          <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
            ✓ Incidencia creada exitosamente. Redirigiendo al listado...
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading || success}
          className="w-full rounded-lg bg-orange-600 px-4 py-3 font-semibold text-white hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? 'Registrando...' : 'Registrar Incidencia'}
        </button>
      </form>
    </div>
  );
}

// ============================================================
// INCIDENTS LIST
// ============================================================

function IncidentsList() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [filters, setFilters] = useState<IncidentFilters>({
    status: undefined,
    origin: undefined,
    branch: undefined,
  });

  const fetchIncidents = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await getIncidents(filters);
      setIncidents(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar incidencias');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, [filters]);

  const handleStatusChange = async (incidentId: string, newStatus: IncidentStatus, currentStatus: IncidentStatus) => {
    // Actualización optimista
    setIncidents((prev) =>
      prev.map((inc) =>
        inc.id === incidentId ? { ...inc, status: newStatus } : inc
      )
    );

    try {
      await updateIncidentStatus(incidentId, { status: newStatus });
      // Refetch para obtener updated_at actualizado
      fetchIncidents();
    } catch (err) {
      // Reversión en caso de error
      setIncidents((prev) =>
        prev.map((inc) =>
          inc.id === incidentId ? { ...inc, status: currentStatus } : inc
        )
      );

      alert(
        err instanceof Error
          ? `Error al actualizar estado: ${err.message}`
          : 'No se pudo actualizar el estado. Transición inválida o error de red.'
      );
    }
  };

  if (loading) {
    return (
      <div className="rounded-lg border border-amber-200 bg-white p-8 text-center">
        <div className="mb-4 inline-block h-12 w-12 animate-spin rounded-full border-4 border-orange-600 border-t-transparent"></div>
        <p className="text-amber-800">Cargando incidencias...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <p className="mb-4 text-red-800">{error}</p>
        <button
          onClick={fetchIncidents}
          className="rounded-lg bg-red-600 px-4 py-2 font-semibold text-white hover:bg-red-700"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="rounded-lg border border-amber-200 bg-white p-4">
        <h3 className="mb-4 font-semibold text-amber-950">Filtros</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-amber-900">Estado</label>
            <select
              value={filters.status || ''}
              onChange={(e) => setFilters({ ...filters, status: e.target.value as IncidentStatus || undefined })}
              className="w-full rounded-lg border border-amber-200 px-3 py-2 text-sm focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500"
            >
              <option value="">Todos</option>
              {STATUSES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-amber-900">Origen</label>
            <select
              value={filters.origin || ''}
              onChange={(e) => setFilters({ ...filters, origin: e.target.value as IncidentOrigin || undefined })}
              className="w-full rounded-lg border border-amber-200 px-3 py-2 text-sm focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500"
            >
              <option value="">Todos</option>
              {ORIGINS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-amber-900">Sede</label>
            <select
              value={filters.branch || ''}
              onChange={(e) => setFilters({ ...filters, branch: e.target.value as IncidentBranch || undefined })}
              className="w-full rounded-lg border border-amber-200 px-3 py-2 text-sm focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500"
            >
              <option value="">Todas</option>
              {BRANCHES.map((b) => (
                <option key={b.value} value={b.value}>{b.label}</option>
              ))}
            </select>
          </div>
        </div>

        <p className="mt-2 text-xs text-amber-700">
          Mostrando {incidents.length} de {total} incidencias
        </p>
      </div>

      {/* Empty State */}
      {incidents.length === 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-8 text-center">
          <p className="text-amber-800">
            {Object.values(filters).some(Boolean)
              ? 'No se encontraron incidencias con los filtros aplicados'
              : 'No hay incidencias registradas aún'}
          </p>
        </div>
      )}

      {/* Incidents Table */}
      {incidents.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-amber-200 bg-white">
          <table className="min-w-full divide-y divide-amber-200">
            <thead className="bg-amber-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-amber-900">Título</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-amber-900">Categoría</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-amber-900">Origen</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-amber-900">Sede</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-amber-900">Estado</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-amber-900">Creado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-amber-100">
              {incidents.map((incident) => {
                const statusObj = STATUSES.find((s) => s.value === incident.status)!;
                const currentStatus = incident.status;

                return (
                  <tr key={incident.id} className="hover:bg-amber-50">
                    <td className="px-4 py-3 text-sm font-medium text-amber-950">
                      {incident.title}
                    </td>
                    <td className="px-4 py-3 text-sm text-amber-800">
                      {CATEGORIES.find((c) => c.value === incident.category)?.label}
                    </td>
                    <td className="px-4 py-3 text-sm text-amber-800">
                      {ORIGINS.find((o) => o.value === incident.origin)?.label}
                    </td>
                    <td className="px-4 py-3 text-sm text-amber-800">
                      {BRANCHES.find((b) => b.value === incident.branch)?.label}
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={incident.status}
                        onChange={(e) =>
                          handleStatusChange(incident.id, e.target.value as IncidentStatus, currentStatus)
                        }
                        className={`rounded-full border px-3 py-1 text-xs font-semibold ${statusObj.color} focus:outline-none focus:ring-2 focus:ring-orange-500`}
                      >
                        {STATUSES.map((s) => (
                          <option key={s.value} value={s.value}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3 text-xs text-amber-700">
                      {new Date(incident.created_at).toLocaleDateString('es-ES', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ============================================================
// INCIDENTS SUMMARY
// ============================================================

function IncidentsSummary() {
  const [summary, setSummary] = useState<IncidentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getIncidentsSummary();
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar métricas');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  if (loading) {
    return (
      <div className="rounded-lg border border-amber-200 bg-white p-8 text-center">
        <div className="mb-4 inline-block h-12 w-12 animate-spin rounded-full border-4 border-orange-600 border-t-transparent"></div>
        <p className="text-amber-800">Calculando métricas...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <p className="mb-4 text-red-800">{error}</p>
        <button
          onClick={fetchSummary}
          className="rounded-lg bg-red-600 px-4 py-2 font-semibold text-white hover:bg-red-700"
        >
          Reintentar
        </button>
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="space-y-6">
      {/* Total */}
      <div className="rounded-lg border-2 border-orange-600 bg-orange-50 p-6 text-center">
        <p className="text-sm font-semibold text-orange-800">Total de Incidencias</p>
        <p className="text-4xl font-bold text-orange-600">{summary.total_incidents}</p>
      </div>

      {/* By Status */}
      <div className="rounded-lg border border-amber-200 bg-white p-6">
        <h3 className="mb-4 font-semibold text-amber-950">Por Estado</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {STATUSES.map((status) => {
            const count = summary.by_status[status.value] || 0;
            return (
              <div key={status.value} className="rounded-lg border border-amber-100 p-4 text-center">
                <p className="text-xs text-amber-700">{status.label}</p>
                <p className="text-2xl font-bold text-amber-950">{count}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* By Category */}
      <div className="rounded-lg border border-amber-200 bg-white p-6">
        <h3 className="mb-4 font-semibold text-amber-950">Por Categoría</h3>
        <div className="space-y-2">
          {CATEGORIES.map((cat) => {
            const count = summary.by_category[cat.value] || 0;
            const percentage = summary.total_incidents > 0 ? (count / summary.total_incidents) * 100 : 0;
            return (
              <div key={cat.value}>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-amber-800">{cat.label}</span>
                  <span className="font-semibold text-amber-950">
                    {count} ({percentage.toFixed(1)}%)
                  </span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-amber-100">
                  <div
                    className="h-2 rounded-full bg-orange-600"
                    style={{ width: `${percentage}%` }}
                  ></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* By Origin */}
      <div className="rounded-lg border border-amber-200 bg-white p-6">
        <h3 className="mb-4 font-semibold text-amber-950">Por Origen</h3>
        <div className="grid grid-cols-3 gap-4">
          {ORIGINS.map((origin) => {
            const count = summary.by_origin[origin.value] || 0;
            return (
              <div key={origin.value} className="rounded-lg border border-amber-100 p-4 text-center">
                <p className="text-xs text-amber-700">{origin.label}</p>
                <p className="text-2xl font-bold text-amber-950">{count}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Satisfaction */}
      {summary.avg_satisfaction !== null && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-6 text-center">
          <p className="text-sm font-semibold text-green-800">Satisfacción Promedio</p>
          <p className="text-4xl font-bold text-green-600">
            {summary.avg_satisfaction.toFixed(2)} / 5.0
          </p>
          <p className="mt-1 text-xs text-green-700">(Solo incidencias resueltas)</p>
        </div>
      )}
    </div>
  );
}
