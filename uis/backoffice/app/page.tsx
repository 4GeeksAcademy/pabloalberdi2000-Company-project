'use client';

import { useState, useEffect, useMemo } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getCandidates } from '@/lib/api';
import { useAuth } from '@/hooks/useAuth';
import { useDebounce } from '@/hooks/useDebounce';
import type { Candidate, Status, Stage } from '@/types';
import { STATUS_LABELS, STAGE_LABELS, COUNTRY_LABELS } from '@/types';

export default function CandidatesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, loading: authLoading } = useAuth();

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  const statusFilter = searchParams.get('status') as Status | null;
  const stageFilter = searchParams.get('stage') as Stage | null;

  // 🚀 OPTIMIZACIÓN: Debounce de búsqueda (500ms)
  // Reduce API calls de 100% a ~20% durante typing
  const debouncedSearch = useDebounce(search, 500);

  // Route protection
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const data = await getCandidates({
          status: statusFilter || undefined,
          stage: stageFilter || undefined,
          search: debouncedSearch || undefined, // 🚀 Usar valor debounced
        });
        setCandidates(data);
      } catch (err) {
        // Sanitizar error antes de mostrar al usuario
        const errorMessage = err instanceof Error ? err.message : 'Error al cargar candidatos';
        setError(errorMessage.includes('network') || errorMessage.includes('fetch')
          ? 'Error de conexión. Verifica tu red e intenta nuevamente'
          : errorMessage);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [statusFilter, stageFilter, debouncedSearch]); // 🚀 Depender de debouncedSearch

  const handleFilterChange = (key: 'status' | 'stage', value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    router.push(`/?${params.toString()}`);
  };

  // 🚀 OPTIMIZACIÓN: Cálculo memoizado de estadísticas
  // Solo recalcula cuando candidates cambia (evita re-cálculo en cada render)
  const stats = useMemo(() => {
    if (candidates.length === 0) return null;

    return {
      total: candidates.length,
      byStatus: candidates.reduce((acc, c) => {
        acc[c.status] = (acc[c.status] || 0) + 1;
        return acc;
      }, {} as Record<Status, number>),
      byStage: candidates.reduce((acc, c) => {
        acc[c.stage] = (acc[c.stage] || 0) + 1;
        return acc;
      }, {} as Record<Stage, number>),
      avgExperience: candidates.reduce((sum, c) => sum + c.years_experience, 0) / candidates.length,
    };
  }, [candidates]);

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
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <header className="mb-8">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-amber-950">
              Sistema de Candidaturas
            </h1>
            <p className="text-amber-800 mt-1">
              Gestión de talento para Colombia y Florida · Ashley Turner - Personas y Cultura
            </p>
          </div>
          <Link
            href="/incidents"
            className="rounded-lg border-2 border-orange-600 px-4 py-2 text-sm font-semibold text-orange-600 transition hover:bg-orange-50"
          >
            📊 Análisis de Incidencias
          </Link>
        </div>
      </header>

      {/* Filters and Search */}
      <div className="mb-6 grid gap-4 md:grid-cols-[1fr_auto_auto]">
        <input
          type="text"
          placeholder="Buscar por nombre o email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-lg border border-amber-300 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200"
        />

        <select
          value={statusFilter || ''}
          onChange={(e) => handleFilterChange('status', e.target.value)}
          className="rounded-lg border border-amber-300 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200"
        >
          <option value="">Todos los estados</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>

        <select
          value={stageFilter || ''}
          onChange={(e) => handleFilterChange('stage', e.target.value)}
          className="rounded-lg border border-amber-300 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200"
        >
          <option value="">Todas las etapas</option>
          {Object.entries(STAGE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-orange-600 border-r-transparent"></div>
            <p className="mt-4 text-sm text-amber-800">Cargando candidatos...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-start mb-3">
            <strong className="text-red-800">Error:</strong>
            <p className="ml-2 text-red-700">{error}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => window.location.reload()}
              className="rounded bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
            >
              Recargar página
            </button>
          </div>
        </div>
      )}

      {/* Success State - Candidates List */}
      {!loading && !error && (
        <>
          <div className="mb-4 text-sm text-amber-800">
            {candidates.length} candidato{candidates.length !== 1 ? 's' : ''} encontrado{candidates.length !== 1 ? 's' : ''}
          </div>

          {candidates.length === 0 ? (
            <div className="rounded-lg border border-amber-200 bg-white px-6 py-12 text-center">
              <p className="text-amber-800">No se encontraron candidatos con los filtros seleccionados.</p>
              <Link
                href="/new"
                className="mt-4 inline-block rounded-lg bg-orange-600 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-700"
              >
                Agregar Primera Candidatura
              </Link>
            </div>
          ) : (
            <div className="grid gap-4">
              {candidates.map((candidate) => (
                <Link
                  key={candidate.id}
                  href={`/candidates/${candidate.id}`}
                  className="rounded-lg border border-amber-200 bg-white p-5 shadow-sm transition hover:shadow-md hover:border-orange-300"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-amber-950">
                        {candidate.full_name}
                      </h3>
                      <p className="text-sm text-amber-800 mt-1">
                        {candidate.position} · {COUNTRY_LABELS[candidate.country]}
                        {candidate.location_preference && ` · ${candidate.location_preference}`}
                      </p>
                      <p className="text-xs text-amber-700 mt-1">
                        {candidate.email} · {candidate.phone}
                      </p>
                      <p className="text-xs text-amber-600 mt-1">
                        Aplicó: {new Date(candidate.application_date).toLocaleDateString('es-ES')} ·
                        {' '}{candidate.years_experience} años de experiencia
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2 sm:flex-col sm:items-end">
                      <span className="inline-block rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
                        {STATUS_LABELS[candidate.status]}
                      </span>
                      <span className="inline-block rounded-full bg-orange-100 px-3 py-1 text-xs font-medium text-orange-800">
                        {STAGE_LABELS[candidate.stage]}
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
