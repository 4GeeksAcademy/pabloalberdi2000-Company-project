import type { Metadata } from 'next';
import { AuthProvider } from '@/contexts/AuthContext';
import { NavBar } from '@/components/NavBar';
import './globals.css';

export const metadata: Metadata = {
  title: 'Brasaland ATS - Sistema de Candidaturas',
  description: 'Sistema de gestión de candidaturas para el departamento de Personas y Cultura de Brasaland',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-amber-50 text-amber-950 antialiased">
        <AuthProvider>
          <NavBar />

          <main>
            {children}
          </main>

          <footer className="border-t border-amber-200 bg-amber-50 mt-auto">
            <div className="mx-auto flex w-full max-w-7xl flex-col gap-2 px-4 py-6 text-xs text-amber-900/80 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
              <p>Brasaland ATS · Sistema de Personas y Cultura</p>
              <p>Medellín y Florida · 14 locales</p>
            </div>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
