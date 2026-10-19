/**
 * TypeScript types for Brasaland ATS frontend
 * These types match the Pydantic schemas from the FastAPI backend
 */

export type Country = 'CO' | 'US';
export type Status = 'activo' | 'archivado' | 'contratado' | 'rechazado';
export type Stage = 'aplicacion' | 'revision' | 'entrevista' | 'oferta' | 'finalizado';

export interface Candidate {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  position: string;
  country: Country;
  location_preference?: string;
  linkedin_url?: string;
  cv_url?: string;
  years_experience: number;
  status: Status;
  stage: Stage;
  application_date: string; // ISO date string
}

export interface Note {
  id: number;
  candidate_id: number;
  content: string;
  author: string;
  created_at: string; // ISO datetime string
}

export interface CandidateFormData {
  full_name: string;
  email: string;
  phone: string;
  position: string;
  country: Country;
  location_preference?: string;
  linkedin_url?: string;
  cv_url?: string;
  years_experience: number;
}

export interface NoteFormData {
  content: string;
  author: string;
}

// UI State types
export interface LoadingState {
  isLoading: boolean;
  error: string | null;
}

// Filter types
export interface CandidateFilters {
  status?: Status;
  stage?: Stage;
  search?: string;
}

// Labels for UI (Spanish - Brasaland context)
export const STATUS_LABELS: Record<Status, string> = {
  activo: 'Activo',
  archivado: 'Archivado',
  contratado: 'Contratado',
  rechazado: 'Rechazado',
};

export const STAGE_LABELS: Record<Stage, string> = {
  aplicacion: 'Aplicación',
  revision: 'Revisión',
  entrevista: 'Entrevista',
  oferta: 'Oferta',
  finalizado: 'Finalizado',
};

export const COUNTRY_LABELS: Record<Country, string> = {
  CO: 'Colombia',
  US: 'Florida, USA',
};

// Position options (typical roles at Brasaland restaurants)
export const POSITION_OPTIONS = [
  'Cocinero',
  'Ayudante de Cocina',
  'Mesero',
  'Cajero',
  'Supervisor',
  'Gerente de Local',
  'Jefe de Cocina',
  'Host/Hostess',
  'Bartender',
  'Limpieza',
] as const;

export type Position = typeof POSITION_OPTIONS[number];
