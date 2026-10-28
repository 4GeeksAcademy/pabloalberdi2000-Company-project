/**
 * useDebounce Hook
 *
 * Debounce de valores para prevenir API calls excesivos.
 * Útil para search inputs y filtros en tiempo real.
 *
 * 🚀 OPTIMIZACIÓN: Reduce API calls en búsqueda de 100% a ~20%
 * - Sin debounce: 1 request por tecla (10 teclas = 10 requests)
 * - Con debounce: 1 request final (10 teclas = 1 request)
 *
 * @example
 * const debouncedSearch = useDebounce(searchInput, 500);
 *
 * useEffect(() => {
 *   fetchResults(debouncedSearch);
 * }, [debouncedSearch]);
 */

import { useState, useEffect } from 'react';

export function useDebounce<T>(value: T, delay: number = 500): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    // Configurar timeout para actualizar valor debounced
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    // Cleanup: cancelar timeout si value cambia antes del delay
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}
