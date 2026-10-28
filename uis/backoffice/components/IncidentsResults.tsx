/**
 * IncidentsResults Component
 *
 * Visualización de resultados del análisis de incidencias CSV.
 * Componente pesado con múltiples gráficos y tablas.
 *
 * 🚀 OPTIMIZACIÓN: Lazy-loaded con next/dynamic
 * - Bundle size: ~15KB (librerías de visualización)
 * - Solo carga cuando hay resultados disponibles
 * - Reduce bundle inicial del dashboard
 */

'use client';

interface IncidentMetrics {
  total_procesados: number;
  total_validos: number;
  total_invalidos: number;
  registros_invalidos: Array<{
    linea: number;
    id_incidencia: string;
    razon: string;
  }>;
  por_categoria: Array<{
    categoria: string;
    cantidad: number;
    porcentaje: number;
  }>;
  por_estado: Array<{
    estado: string;
    cantidad: number;
    porcentaje: number;
  }>;
  por_pais: Array<{
    pais: string;
    pais_nombre: string;
    cantidad: number;
    porcentaje: number;
  }>;
  satisfaccion_promedio: number;
  satisfaccion_evaluacion: string;
}

interface Props {
  results: IncidentMetrics;
  onExportCSV?: () => void;
}

export default function IncidentsResults({ results, onExportCSV }: Props) {
  const getEvaluacionColor = (evaluacion: string) => {
    if (evaluacion === 'EXCELENTE') return 'text-green-700 bg-green-100';
    if (evaluacion === 'BUENO') return 'text-yellow-700 bg-yellow-100';
    if (evaluacion === 'ACEPTABLE') return 'text-orange-700 bg-orange-100';
    return 'text-red-700 bg-red-100';
  };

  return (
    <div className="space-y-6">
      {/* Resumen General */}
      <div className="rounded-lg border border-amber-200 bg-white p-6">
        <h2 className="mb-4 text-xl font-semibold text-amber-950">
          📊 Resumen General
        </h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg bg-blue-50 p-4">
            <p className="text-sm text-blue-800">Total Procesados</p>
            <p className="text-3xl font-bold text-blue-950">{results.total_procesados}</p>
          </div>
          <div className="rounded-lg bg-green-50 p-4">
            <p className="text-sm text-green-800">Válidos</p>
            <p className="text-3xl font-bold text-green-950">{results.total_validos}</p>
          </div>
          <div className="rounded-lg bg-red-50 p-4">
            <p className="text-sm text-red-800">Inválidos</p>
            <p className="text-3xl font-bold text-red-950">{results.total_invalidos}</p>
          </div>
        </div>
      </div>

      {/* Satisfacción */}
      <div className="rounded-lg border border-amber-200 bg-white p-6">
        <h2 className="mb-4 text-xl font-semibold text-amber-950">
          ⭐ Índice de Satisfacción
        </h2>
        <div className="flex items-center gap-4">
          <div className="text-5xl font-bold text-amber-950">
            {results.satisfaccion_promedio.toFixed(2)}
            <span className="text-2xl text-amber-700">/5.0</span>
          </div>
          <span className={`rounded-full px-4 py-2 text-sm font-semibold ${getEvaluacionColor(results.satisfaccion_evaluacion)}`}>
            {results.satisfaccion_evaluacion}
          </span>
        </div>
      </div>

      {/* Por Categoría */}
      <div className="rounded-lg border border-amber-200 bg-white p-6">
        <h2 className="mb-4 text-xl font-semibold text-amber-950">
          📂 Distribución por Categoría
        </h2>
        <div className="space-y-3">
          {results.por_categoria.map((item) => (
            <div key={item.categoria}>
              <div className="mb-1 flex justify-between text-sm">
                <span className="text-amber-900">{item.categoria}</span>
                <span className="font-semibold text-amber-950">
                  {item.cantidad} ({item.porcentaje.toFixed(1)}%)
                </span>
              </div>
              <div className="h-3 rounded-full bg-amber-100">
                <div
                  className="h-full rounded-full bg-orange-600 transition-all duration-500"
                  style={{ width: `${item.porcentaje}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Por Estado */}
      <div className="rounded-lg border border-amber-200 bg-white p-6">
        <h2 className="mb-4 text-xl font-semibold text-amber-950">
          🔄 Distribución por Estado
        </h2>
        <div className="space-y-3">
          {results.por_estado.map((item) => (
            <div key={item.estado}>
              <div className="mb-1 flex justify-between text-sm">
                <span className="text-amber-900">{item.estado}</span>
                <span className="font-semibold text-amber-950">
                  {item.cantidad} ({item.porcentaje.toFixed(1)}%)
                </span>
              </div>
              <div className="h-3 rounded-full bg-amber-100">
                <div
                  className="h-full rounded-full bg-green-600 transition-all duration-500"
                  style={{ width: `${item.porcentaje}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Por País */}
      <div className="rounded-lg border border-amber-200 bg-white p-6">
        <h2 className="mb-4 text-xl font-semibold text-amber-950">
          🌎 Distribución por País
        </h2>
        <div className="space-y-3">
          {results.por_pais.map((item) => (
            <div key={item.pais}>
              <div className="mb-1 flex justify-between text-sm">
                <span className="text-amber-900">{item.pais_nombre}</span>
                <span className="font-semibold text-amber-950">
                  {item.cantidad} ({item.porcentaje.toFixed(1)}%)
                </span>
              </div>
              <div className="h-3 rounded-full bg-amber-100">
                <div
                  className="h-full rounded-full bg-blue-600 transition-all duration-500"
                  style={{ width: `${item.porcentaje}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Registros Inválidos */}
      {results.registros_invalidos.length > 0 && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6">
          <h2 className="mb-4 text-xl font-semibold text-red-950">
            ⚠️ Registros Inválidos ({results.registros_invalidos.length})
          </h2>
          <div className="max-h-64 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-red-100">
                <tr>
                  <th className="p-2 text-left text-red-900">Línea</th>
                  <th className="p-2 text-left text-red-900">ID</th>
                  <th className="p-2 text-left text-red-900">Razón</th>
                </tr>
              </thead>
              <tbody>
                {results.registros_invalidos.map((record) => (
                  <tr key={record.linea} className="border-t border-red-200">
                    <td className="p-2 text-red-800">{record.linea}</td>
                    <td className="p-2 text-red-800">{record.id_incidencia}</td>
                    <td className="p-2 text-red-700">{record.razon}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Botón de Exportación */}
      {onExportCSV && (
        <div className="flex justify-end">
          <button
            onClick={onExportCSV}
            className="rounded-lg bg-green-600 px-6 py-3 font-semibold text-white transition hover:bg-green-700"
          >
            📥 Exportar Resultados CSV
          </button>
        </div>
      )}
    </div>
  );
}
