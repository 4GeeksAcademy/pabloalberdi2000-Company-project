'use client';

import { useState } from 'react';
import Link from 'next/link';
import { requestPasswordReset } from '@/lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await requestPasswordReset(email);
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al enviar solicitud');
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="container mx-auto flex min-h-screen items-center justify-center px-4">
        <div className="w-full max-w-md rounded-lg border border-green-200 bg-green-50 p-8 shadow-lg">
          <div className="mb-4 text-center text-4xl">✉️</div>
          <h1 className="mb-4 text-center text-2xl font-bold text-green-900">
            Revisa tu correo
          </h1>
          <p className="mb-6 text-center text-green-800">
            Si esa dirección está registrada, recibirás un enlace de restablecimiento en breve.
          </p>
          <Link
            href="/login"
            className="block w-full rounded-lg border-2 border-orange-600 px-4 py-3 text-center font-semibold text-orange-600 hover:bg-orange-50"
          >
            Volver al inicio de sesión
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md rounded-lg border border-amber-200 bg-white p-8 shadow-lg">
        <h1 className="mb-2 text-2xl font-bold text-amber-950">
          ¿Olvidaste tu contraseña?
        </h1>
        <p className="mb-6 text-sm text-amber-800">
          Ingresa tu email y te enviaremos un enlace para restablecer tu contraseña.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="mb-1 block text-sm font-medium text-amber-900">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-amber-200 px-4 py-2 focus:border-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500"
              placeholder="tu@email.com"
            />
          </div>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-orange-600 px-4 py-3 font-semibold text-white hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? 'Enviando...' : 'Enviar enlace de restablecimiento'}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-amber-800">
          <Link href="/login" className="font-semibold text-orange-600 hover:text-orange-700 hover:underline">
            Volver al inicio de sesión
          </Link>
        </p>
      </div>
    </div>
  );
}
