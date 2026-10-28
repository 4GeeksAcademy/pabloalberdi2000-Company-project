/**
 * IncidentsResultsSkeleton Component
 *
 * Skeleton loader para IncidentsResults durante lazy loading.
 * Previene layout shift y mejora perceived performance.
 */

'use client';

export default function IncidentsResultsSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Resumen General Skeleton */}
      <div className="rounded-lg border border-amber-200 bg-white p-6">
        <div className="mb-4 h-6 w-48 bg-amber-200 rounded"></div>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg bg-blue-50 p-4">
            <div className="h-4 w-32 bg-blue-200 rounded mb-2"></div>
            <div className="h-10 w-20 bg-blue-300 rounded"></div>
          </div>
          <div className="rounded-lg bg-green-50 p-4">
            <div className="h-4 w-32 bg-green-200 rounded mb-2"></div>
            <div className="h-10 w-20 bg-green-300 rounded"></div>
          </div>
          <div className="rounded-lg bg-red-50 p-4">
            <div className="h-4 w-32 bg-red-200 rounded mb-2"></div>
            <div className="h-10 w-20 bg-red-300 rounded"></div>
          </div>
        </div>
      </div>

      {/* Satisfacción Skeleton */}
      <div className="rounded-lg border border-amber-200 bg-white p-6">
        <div className="mb-4 h-6 w-56 bg-amber-200 rounded"></div>
        <div className="flex items-center gap-4">
          <div className="h-16 w-32 bg-amber-200 rounded"></div>
          <div className="h-8 w-28 bg-amber-200 rounded-full"></div>
        </div>
      </div>

      {/* Gráficos Skeleton */}
      {[1, 2, 3].map((i) => (
        <div key={i} className="rounded-lg border border-amber-200 bg-white p-6">
          <div className="mb-4 h-6 w-64 bg-amber-200 rounded"></div>
          <div className="space-y-3">
            {[1, 2, 3, 4].map((j) => (
              <div key={j}>
                <div className="mb-1 flex justify-between">
                  <div className="h-4 w-32 bg-amber-100 rounded"></div>
                  <div className="h-4 w-24 bg-amber-100 rounded"></div>
                </div>
                <div className="h-3 w-full bg-amber-100 rounded-full"></div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
