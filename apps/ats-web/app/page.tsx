'use client';

import { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getCandidates } from '@/lib/api';
import type { Candidate, Status, Stage } from '@/types';
import { STATUS_LABELS, STAGE_LABELS, COUNTRY_LABELS } from '@/types';

export default function CandidatesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  const statusFilter = searchParams.get('status') as Status | null;
  const stageFilter = searchParams.get('stage') as Stage | null;

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const data = await getCandidates({
          status: statusFilter || undefined,
          stage: stageFilter || undefined,
          search: search || undefined,
        });
        setCandidates(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error desconocido');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [statusFilter, stageFilter, search]);

  const handleFilterChange = (key: 'status' | 'stage', value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    router.push(`/?${params.toString()}`);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-amber-950">
          Sistema de Candidaturas
        </h1>
        <p className="text-amber-800 mt-1">
          Gestión de talento para Colombia y Florida · Ashley Turner - Personas y Cultura
        </p>
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
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <strong>Error:</strong> {error}
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
