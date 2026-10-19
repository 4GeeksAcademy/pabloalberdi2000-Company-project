import type { Metadata } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'Brasaland ATS - Sistema de Candidaturas',
  description: 'Sistema de gestión de candidaturas para el departamento de Personas y Cultura de Brasaland',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.Node;
}>) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-amber-50 text-amber-950 antialiased">
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
                <Link
                  href="/"
                  className="text-sm text-amber-800 hover:text-amber-950 transition"
                >
                  Candidatos
                </Link>
                <Link
                  href="/new"
                  className="rounded-lg bg-orange-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-600 focus:ring-offset-2"
                >
                  Nueva Candidatura
                </Link>
              </div>
            </div>
          </nav>
        </header>

        <main>
          {children}
        </main>

        <footer className="border-t border-amber-200 bg-amber-50 mt-auto">
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-2 px-4 py-6 text-xs text-amber-900/80 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
            <p>Brasaland ATS · Sistema de Personas y Cultura</p>
            <p>Medellín y Florida · 14 locales</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
