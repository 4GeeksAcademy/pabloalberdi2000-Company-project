'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { updateProfile } from '@/lib/api';

export default function ProfilePage() {
  const router = useRouter();
  const { user, isAuthenticated, loading: authLoading } = useAuth();

  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Route protection
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, authLoading, router]);

  // Load initial data
  useEffect(() => {
    if (user?.profile) {
      setName(user.profile.name || '');
      setPhone(user.profile.phone || '');
      setAddress(user.profile.address || '');
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      await updateProfile({ name, phone, address });
      setSuccess(true);

      // Auto-hide success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al actualizar perfil');
    } finally {
      setLoading(false);
    }
  };

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

  if (!user) {
    return null;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="mb-6 text-3xl font-bold text-amber-950">Mi Perfil</h1>

      {/* Non-editable info */}
      <div className="mb-8 rounded-lg border border-amber-200 bg-white p-6">
        <h2 className="mb-4 text-xl font-semibold text-amber-950">Información de Cuenta</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-amber-800">Email</label>
            <p className="mt-1 text-lg text-amber-950">{user.email}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-amber-800">Rol</label>
            <p className="mt-1 text-lg text-amber-950">
              {user.role === 'admin' && 'Administrador'}
              {user.role === 'manager' && 'Manager'}
              {user.role === 'user' && 'Usuario'}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-amber-800">Estado</label>
            <p className="mt-1 text-lg">
              {user.is_active ? (
                <span className="inline-flex items-center rounded-full bg-green-100 px-3 py-1 text-sm font-semibold text-green-800">
                  Activo
                </span>
              ) : (
                <span className="inline-flex items-center rounded-full bg-red-100 px-3 py-1 text-sm font-semibold text-red-800">
                  Inactivo
                </span>
              )}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-amber-800">Miembro desde</label>
            <p className="mt-1 text-lg text-amber-950">
              {new Date(user.created_at).toLocaleDateString('es-ES', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </div>
        </div>
      </div>

      {/* Editable profile form */}
      <form onSubmit={handleSubmit} className="rounded-lg border border-amber-200 bg-white p-6">
        <h2 className="mb-4 text-xl font-semibold text-amber-950">Información Personal</h2>

        <div className="space-y-4">
          <div>
            <label htmlFor="name" className="mb-1 block text-sm font-medium text-amber-900">
              Nombre Completo
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-amber-200 px-4 py-2 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500"
              placeholder="Tu nombre completo"
            />
          </div>

          <div>
            <label htmlFor="phone" className="mb-1 block text-sm font-medium text-amber-900">
              Teléfono
            </label>
            <input
              id="phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full rounded-lg border border-amber-200 px-4 py-2 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500"
              placeholder="+57 123 456 7890"
            />
          </div>

          <div>
            <label htmlFor="address" className="mb-1 block text-sm font-medium text-amber-900">
              Dirección
            </label>
            <input
              id="address"
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="w-full rounded-lg border border-amber-200 px-4 py-2 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500"
              placeholder="Calle 123 #45-67, Bogotá"
            />
          </div>
        </div>

        {success && (
          <div className="mt-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
            ✓ Perfil actualizado correctamente
          </div>
        )}

        {error && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="mt-6 w-full rounded-lg bg-orange-600 px-4 py-3 font-semibold text-white hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
        >
          {loading ? 'Guardando...' : 'Guardar Cambios'}
        </button>
      </form>
    </div>
  );
}
