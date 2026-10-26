'use client';

import React, { createContext, useState, useEffect, ReactNode } from 'react';
import {
  User,
  RegisterData,
  login as apiLogin,
  register as apiRegister,
  getCurrentUser,
} from '@/lib/api';
import { getToken, setToken, removeToken } from '@/lib/auth';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Check for existing token on mount
  useEffect(() => {
    async function loadUser() {
      const token = getToken();
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const userData = await getCurrentUser();
        setUser(userData);
      } catch (error) {
        // Token invalid or expired - clean up
        console.error('Failed to load user on mount:', error);
        removeToken();
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response = await apiLogin({ email, password });
      setToken(response.access_token);

      // Load user data
      const userData = await getCurrentUser();
      setUser(userData);
    } catch (error) {
      // Clean up on failure
      removeToken();
      throw error; // Re-throw para que el componente lo maneje
    }
  };

  const register = async (data: RegisterData) => {
    try {
      // Create user
      await apiRegister(data);

      // Auto-login after registration
      await login(data.email, data.password);
    } catch (error) {
      console.error('Registration or auto-login failed:', error);
      throw error; // Re-throw para que el componente lo maneje
    }
  };

  const logout = () => {
    removeToken();
    setUser(null);
    window.location.href = '/login';
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
