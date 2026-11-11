/**
 * useAuth Hook - Client-side Auth Guard
 *
 * Verifica que el usuario tenga token JWT válido.
 * Si no está autenticado, redirige a /login automáticamente.
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getToken, setToken, removeToken } from '@/lib/auth';

const API_URL = process.env.NEXT_PUBLIC_EXTERNAL_API_URL || 'http://localhost:8000';

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    // Initialize state from localStorage immediately
    if (typeof window !== 'undefined') {
      return !!getToken();
    }
    return false;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const router = useRouter();

  useEffect(() => {
    const checkAuth = () => {
      const token = getToken();
      console.log('🔍 useAuth checking token:', token ? 'Token exists' : 'No token');
      console.log('🔍 Token value:', token);
      setIsAuthenticated(!!token);
      setIsLoading(false);
    };

    checkAuth();
  }, []); // Solo verificar token una vez al montar

  const login = async (email: string, password: string) => {
    const response = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Error al iniciar sesión');
    }

    const data = await response.json();
    setToken(data.access_token);
    setIsAuthenticated(true);
  };

  const logout = () => {
    removeToken();
    setIsAuthenticated(false);
    router.push('/login');
  };

  const token = typeof window !== 'undefined' ? getToken() : null;

  return { isAuthenticated, isLoading, login, logout, token };
}
