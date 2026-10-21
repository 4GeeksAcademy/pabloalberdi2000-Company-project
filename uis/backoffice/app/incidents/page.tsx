'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';

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

export default function IncidentsPage() {
  const router = useRouter();
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<IncidentMetrics | null>(null);

  // Route protection
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.csv')) {
        setError('El archivo debe ser un CSV (.csv)');
        setFile(null);
        return;
      }
      setFile(selectedFile);
      setError(null);
      setResults(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file) {
      setError('Por favor selecciona un archivo CSV');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('http://localhost:8000/incidents/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Error al analizar el archivo');
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido al analizar');
    } finally {
      setLoading(false);
    }
  };

  const getEvaluacionColor = (evaluacion: string) => {
    if (evaluacion === 'EXCELENTE') return 'text-green-700 bg-green-100';
    if (evaluacion === 'BUENO') return 'text-yellow-700 bg-yellow-100';
    return 'text-red-700 bg-red-100';
  };

  const exportToCSV = () => {
    if (!results) return;

    const rows = [
      ['Métrica', 'Valor'],
      ['Total Procesados', results.total_procesados.toString()],
      ['Total Válidos', results.total_validos.toString()],
      ['Total Inválidos', results.total_invalidos.toString()],
      [],
      ['CATEGORÍA', 'CANTIDAD', 'PORCENTAJE'],
      ...results.por_categoria.map(c => [c.categoria, c.cantidad.toString(), `${c.porcentaje.toFixed(1)}%`]),
      [],
      ['ESTADO', 'CANTIDAD', 'PORCENTAJE'],
      ...results.por_estado.map(e => [e.estado, e.cantidad.toString(), `${e.porcentaje.toFixed(1)}%`]),
      [],
      ['PAÍS', 'CANTIDAD', 'PORCENTAJE'],
      ...results.por_pais.map(p => [p.pais_nombre, p.cantidad.toString(), `${p.porcentaje.toFixed(1)}%`]),
      [],
      ['SATISFACCIÓN PROMEDIO', results.satisfaccion_promedio.toFixed(2)],
      ['EVALUACIÓN', results.satisfaccion_evaluacion]
    ];

    const csvContent = rows.map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `resultados-incidencias-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  // Don't render if not authenticated
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
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <Link
        href="/"
        className="inline-block mb-6 text-sm text-orange-600 hover:text-orange-700 transition"
      >
        ← Volver al ATS
      </Link>

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-amber-950 mb-2">
          Análisis de Incidencias Postventa
        </h1>
        <p className="text-amber-800">
          Sube un archivo CSV con incidencias para obtener métricas y validaciones
        </p>
      </div>

      {/* Upload Section */}
      <div className="rounded-lg border border-amber-200 bg-white shadow-sm p-6 mb-6">
        <h2 className="text-xl font-semibold text-amber-950 mb-4">
          Subir Archivo CSV
        </h2>

        <div className="space-y-4">
          <div>
            <input
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="block w-full text-sm text-amber-900
                file:mr-4 file:py-2 file:px-4
                file:rounded-lg file:border-0
                file:text-sm file:font-semibold
                file:bg-orange-600 file:text-white
                hover:file:bg-orange-700
                file:cursor-pointer cursor-pointer"
            />
            {file && (
              <p className="mt-2 text-sm text-amber-700">
                ✓ Archivo seleccionado: <span className="font-semibold">{file.name}</span>
              </p>
            )}
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleAnalyze}
              disabled={!file || loading}
              className="flex-1 rounded-lg bg-orange-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-600 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Analizando...' : 'Analizar Incidencias'}
            </button>

            {results && (
              <button
                onClick={exportToCSV}
                className="rounded-lg bg-green-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-600 focus:ring-offset-2"
              >
                📥 Descargar CSV
              </button>
            )}
          </div>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <strong>Error:</strong> {error}
            </div>
          )}
        </div>
      </div>

      {/* Results Section */}
      {results && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="rounded-lg border border-amber-200 bg-white shadow-sm p-6">
              <h3 className="text-sm font-semibold text-amber-900 mb-2">
                Total Procesados
              </h3>
              <p className="text-3xl font-bold text-amber-950">
                {results.total_procesados}
              </p>
            </div>

            <div className="rounded-lg border border-green-200 bg-green-50 shadow-sm p-6">
              <h3 className="text-sm font-semibold text-green-900 mb-2">
                Registros Válidos
              </h3>
              <p className="text-3xl font-bold text-green-700">
                {results.total_validos}
              </p>
            </div>

            <div className="rounded-lg border border-red-200 bg-red-50 shadow-sm p-6">
              <h3 className="text-sm font-semibold text-red-900 mb-2">
                Registros Inválidos
              </h3>
              <p className="text-3xl font-bold text-red-700">
                {results.total_invalidos}
              </p>
            </div>
          </div>

          {/* Satisfaction */}
          <div className="rounded-lg border border-amber-200 bg-white shadow-sm p-6">
            <h3 className="text-lg font-semibold text-amber-950 mb-4">
              Índice de Satisfacción
            </h3>
            <div className="flex items-center gap-4">
              <div>
                <p className="text-4xl font-bold text-orange-600">
                  {results.satisfaccion_promedio.toFixed(2)}
                </p>
                <p className="text-sm text-amber-700">sobre 5.00</p>
              </div>
              <div>
                <span
                  className={`inline-block px-4 py-2 rounded-lg font-semibold ${getEvaluacionColor(
                    results.satisfaccion_evaluacion
                  )}`}
                >
                  {results.satisfaccion_evaluacion}
                </span>
              </div>
            </div>
          </div>

          {/* Invalid Records */}
          {results.total_invalidos > 0 && (
            <div className="rounded-lg border border-red-200 bg-red-50 shadow-sm p-6">
              <h3 className="text-lg font-semibold text-red-900 mb-4">
                Registros Inválidos Detectados
              </h3>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {results.registros_invalidos.map((inv, idx) => (
                  <div
                    key={idx}
                    className="text-sm bg-white rounded p-3 border border-red-100"
                  >
                    <span className="font-semibold">Línea {inv.linea}</span> |
                    ID: {inv.id_incidencia} | {inv.razon}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metrics Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Por Categoría */}
            <div className="rounded-lg border border-amber-200 bg-white shadow-sm p-6">
              <h3 className="text-lg font-semibold text-amber-950 mb-4">
                Por Categoría
              </h3>
              <div className="space-y-3">
                {results.por_categoria.map((cat) => (
                  <div key={cat.categoria} className="flex justify-between items-center">
                    <span className="text-sm text-amber-900 capitalize">
                      {cat.categoria.replace('_', ' ')}
                    </span>
                    <div className="text-right">
                      <span className="text-sm font-semibold text-amber-950">
                        {cat.cantidad}
                      </span>
                      <span className="text-xs text-amber-700 ml-2">
                        ({cat.porcentaje.toFixed(1)}%)
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Por Estado */}
            <div className="rounded-lg border border-amber-200 bg-white shadow-sm p-6">
              <h3 className="text-lg font-semibold text-amber-950 mb-4">
                Por Estado
              </h3>
              <div className="space-y-3">
                {results.por_estado.map((est) => (
                  <div key={est.estado} className="flex justify-between items-center">
                    <span className="text-sm text-amber-900 capitalize">
                      {est.estado.replace('_', ' ')}
                    </span>
                    <div className="text-right">
                      <span className="text-sm font-semibold text-amber-950">
                        {est.cantidad}
                      </span>
                      <span className="text-xs text-amber-700 ml-2">
                        ({est.porcentaje.toFixed(1)}%)
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Por País */}
            <div className="rounded-lg border border-amber-200 bg-white shadow-sm p-6">
              <h3 className="text-lg font-semibold text-amber-950 mb-4">
                Por País
              </h3>
              <div className="space-y-3">
                {results.por_pais.map((pais) => (
                  <div key={pais.pais} className="flex justify-between items-center">
                    <span className="text-sm text-amber-900">
                      {pais.pais_nombre}
                    </span>
                    <div className="text-right">
                      <span className="text-sm font-semibold text-amber-950">
                        {pais.cantidad}
                      </span>
                      <span className="text-xs text-amber-700 ml-2">
                        ({pais.porcentaje.toFixed(1)}%)
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
