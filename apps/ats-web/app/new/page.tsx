'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { createCandidate } from '@/lib/api';
import type { CandidateFormData, Country } from '@/types';
import { POSITION_OPTIONS } from '@/types';

export default function NewCandidatePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [formData, setFormData] = useState<CandidateFormData>({
    full_name: '',
    email: '',
    phone: '',
    position: '',
    country: 'CO',
    location_preference: '',
    linkedin_url: '',
    cv_url: '',
    years_experience: 0,
  });

  const [errors, setErrors] = useState<Partial<Record<keyof CandidateFormData, string>>>({});

  const validateForm = (): boolean => {
    const newErrors: Partial<Record<keyof CandidateFormData, string>> = {};

    if (!formData.full_name.trim()) {
      newErrors.full_name = 'El nombre completo es obligatorio';
    } else if (formData.full_name.trim().length < 3) {
      newErrors.full_name = 'El nombre debe tener al menos 3 caracteres';
    }

    if (!formData.email.trim()) {
      newErrors.email = 'El email es obligatorio';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Ingresa un email válido';
    }

    if (!formData.phone.trim()) {
      newErrors.phone = 'El teléfono es obligatorio';
    }

    if (!formData.position) {
      newErrors.position = 'Selecciona un puesto';
    }

    if (formData.years_experience < 0) {
      newErrors.years_experience = 'Los años de experiencia no pueden ser negativos';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const newCandidate = await createCandidate(formData);
      setSuccess(true);

      // Redirect to detail page after 1 second
      setTimeout(() => {
        router.push(`/candidates/${newCandidate.id}`);
      }, 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear candidatura');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (field: keyof CandidateFormData, value: string | number) => {
    setFormData({ ...formData, [field]: value });
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors({ ...errors, [field]: undefined });
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <Link
        href="/"
        className="inline-block mb-6 text-sm text-orange-600 hover:text-orange-700 transition"
      >
        ← Volver al listado
      </Link>

      <div className="rounded-lg border border-amber-200 bg-white shadow-sm p-6">
        <h1 className="text-3xl font-bold text-amber-950 mb-2">Nueva Candidatura</h1>
        <p className="text-amber-800 mb-6">
          Completa el formulario para agregar un nuevo candidato al sistema
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Personal Information */}
          <div className="border-b border-amber-100 pb-6">
            <h2 className="text-lg font-semibold text-amber-950 mb-4">Información Personal</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-amber-900 mb-1">
                  Nombre completo <span className="text-red-600">*</span>
                </label>
                <input
                  type="text"
                  value={formData.full_name}
                  onChange={(e) => handleInputChange('full_name', e.target.value)}
                  className={`w-full rounded-lg border ${
                    errors.full_name ? 'border-red-500' : 'border-amber-300'
                  } bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200`}
                />
                {errors.full_name && (
                  <p className="mt-1 text-xs text-red-600">{errors.full_name}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-semibold text-amber-900 mb-1">
                  Email <span className="text-red-600">*</span>
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleInputChange('email', e.target.value)}
                  className={`w-full rounded-lg border ${
                    errors.email ? 'border-red-500' : 'border-amber-300'
                  } bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200`}
                />
                {errors.email && (
                  <p className="mt-1 text-xs text-red-600">{errors.email}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-semibold text-amber-900 mb-1">
                  Teléfono <span className="text-red-600">*</span>
                </label>
                <input
                  type="tel"
                  value={formData.phone}
                  onChange={(e) => handleInputChange('phone', e.target.value)}
                  placeholder="+57 300 123 4567"
                  className={`w-full rounded-lg border ${
                    errors.phone ? 'border-red-500' : 'border-amber-300'
                  } bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200`}
                />
                {errors.phone && (
                  <p className="mt-1 text-xs text-red-600">{errors.phone}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-semibold text-amber-900 mb-1">
                  Años de experiencia <span className="text-red-600">*</span>
                </label>
                <input
                  type="number"
                  min="0"
                  value={formData.years_experience}
                  onChange={(e) => handleInputChange('years_experience', parseInt(e.target.value) || 0)}
                  className={`w-full rounded-lg border ${
                    errors.years_experience ? 'border-red-500' : 'border-amber-300'
                  } bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200`}
                />
                {errors.years_experience && (
                  <p className="mt-1 text-xs text-red-600">{errors.years_experience}</p>
                )}
              </div>
            </div>
          </div>

          {/* Position Information */}
          <div className="border-b border-amber-100 pb-6">
            <h2 className="text-lg font-semibold text-amber-950 mb-4">Información del Puesto</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-amber-900 mb-1">
                  Puesto solicitado <span className="text-red-600">*</span>
                </label>
                <select
                  value={formData.position}
                  onChange={(e) => handleInputChange('position', e.target.value)}
                  className={`w-full rounded-lg border ${
                    errors.position ? 'border-red-500' : 'border-amber-300'
                  } bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200`}
                >
                  <option value="">Selecciona un puesto</option>
                  {POSITION_OPTIONS.map((position) => (
                    <option key={position} value={position}>
                      {position}
                    </option>
                  ))}
                </select>
                {errors.position && (
                  <p className="mt-1 text-xs text-red-600">{errors.position}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-semibold text-amber-900 mb-1">
                  País <span className="text-red-600">*</span>
                </label>
                <select
                  value={formData.country}
                  onChange={(e) => handleInputChange('country', e.target.value as Country)}
                  className="w-full rounded-lg border border-amber-300 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200"
                >
                  <option value="CO">Colombia</option>
                  <option value="US">Florida, Estados Unidos</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-semibold text-amber-900 mb-1">
                  Preferencia de local (opcional)
                </label>
                <input
                  type="text"
                  value={formData.location_preference}
                  onChange={(e) => handleInputChange('location_preference', e.target.value)}
                  placeholder="Ej: Medellín Centro, Miami Beach"
                  className="w-full rounded-lg border border-amber-300 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200"
                />
              </div>
            </div>
          </div>

          {/* Additional Information */}
          <div>
            <h2 className="text-lg font-semibold text-amber-950 mb-4">Información Adicional</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-amber-900 mb-1">
                  LinkedIn (opcional)
                </label>
                <input
                  type="url"
                  value={formData.linkedin_url}
                  onChange={(e) => handleInputChange('linkedin_url', e.target.value)}
                  placeholder="https://linkedin.com/in/..."
                  className="w-full rounded-lg border border-amber-300 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-amber-900 mb-1">
                  URL del CV (opcional)
                </label>
                <input
                  type="url"
                  value={formData.cv_url}
                  onChange={(e) => handleInputChange('cv_url', e.target.value)}
                  placeholder="https://drive.google.com/..."
                  className="w-full rounded-lg border border-amber-300 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200"
                />
              </div>
            </div>
          </div>

          {/* Error/Success Messages */}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <strong>Error:</strong> {error}
            </div>
          )}

          {success && (
            <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
              ✓ Candidatura creada exitosamente. Redirigiendo...
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-4 pt-4">
            <button
              type="submit"
              disabled={loading || success}
              className="flex-1 rounded-lg bg-orange-600 px-6 py-3 text-sm font-semibold text-white transition hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-600 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creando...' : success ? 'Creado ✓' : 'Crear Candidatura'}
            </button>
            <Link
              href="/"
              className="rounded-lg border border-amber-300 px-6 py-3 text-sm font-semibold text-amber-900 transition hover:bg-amber-50 focus:outline-none focus:ring-2 focus:ring-orange-600 focus:ring-offset-2"
            >
              Cancelar
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
