/**
 * useAuth Hook - Client-side Auth Guard
 * 
 * Verifica que el usuario tenga token JWT válido.
 * Si no está autenticado, redirige a /login automáticamente.
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken } from '@/lib/auth';

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const router = useRouter();

  useEffect(() => {
    const token = getToken();

    if (!token) {
      router.push('/login');
      setIsAuthenticated(false);
      setIsLoading(false);
      return;
    }

    setIsAuthenticated(true);
    setIsLoading(false);
  }, [router]);

  return { isAuthenticated, isLoading };
}
