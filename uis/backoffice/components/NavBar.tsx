'use client';

import Link from 'next/link';
import { useAuth } from '@/hooks/useAuth';

export function NavBar() {
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <header className="sticky top-0 z-30 border-b border-amber-200 bg-amber-50/95 backdrop-blur">
      <nav className="mx-auto w-full max-w-7xl px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between">
          <Link
            href="/"
            className="text-base font-semibold tracking-tight sm:text-lg hover:text-orange-600 transition"
          >
            Brasaland ATS
          </Link>

          <div className="flex items-center gap-4">
            {isAuthenticated ? (
              <>
                <Link
                  href="/"
                  className="text-sm text-amber-800 hover:text-amber-950 transition"
                >
                  Candidatos
                </Link>
                <Link
                  href="/new"
                  className="text-sm text-amber-800 hover:text-amber-950 transition"
                >
                  Nueva Candidatura
                </Link>
                <Link
                  href="/incidents"
                  className="text-sm text-amber-800 hover:text-amber-950 transition"
                >
                  Incidencias
                </Link>

                <div className="mx-2 h-6 w-px bg-amber-300"></div>

                <span className="text-sm text-amber-800">
                  {user?.profile?.name || user?.email}
                </span>
                <Link
                  href="/account/profile"
                  className="text-sm text-amber-800 hover:text-amber-950 transition"
                >
                  Mi Perfil
                </Link>
                <button
                  onClick={logout}
                  className="text-sm font-medium text-red-600 hover:text-red-700 transition"
                >
                  Cerrar Sesión
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="text-sm text-amber-800 hover:text-amber-950 transition"
                >
                  Iniciar Sesión
                </Link>
                <Link
                  href="/register"
                  className="rounded-lg bg-orange-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-600 focus:ring-offset-2"
                >
                  Registrarse
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>
    </header>
  );
}
