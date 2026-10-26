/**
 * API Client for Brasaland ATS
 * All functions use async/await and handle loading/success/error states
 */

import type {
  Candidate,
  Note,
  CandidateFormData,
  NoteFormData,
  Status,
  Stage,
  CandidateFilters,
} from '@/types';
import { getToken, removeToken } from './auth';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Generic fetch wrapper with error handling
 * Automatically injects JWT token if available
 */
async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  // Inject Authorization header if token exists
  const token = getToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
    ...options?.headers,
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Handle 401 Unauthorized - Token invalid or expired
    if (response.status === 401) {
      removeToken();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
      throw new Error('Sesión expirada. Por favor, inicia sesión nuevamente.');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Error desconocido' }));
      throw new Error(error.detail || `Error ${response.status}: ${response.statusText}`);
    }

    // For 204 No Content responses
    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Error de conexión con el servidor');
  }
}

// ============ CANDIDATES API ============

/**
 * Get all candidates with optional filters
 */
export async function getCandidates(filters?: CandidateFilters): Promise<Candidate[]> {
  const params = new URLSearchParams();

  if (filters?.status) {
    params.set('status', filters.status);
  }
  if (filters?.stage) {
    params.set('stage', filters.stage);
  }
  if (filters?.search) {
    params.set('search', filters.search);
  }

  const queryString = params.toString();
  const endpoint = queryString ? `/records?${queryString}` : '/records';

  return fetchAPI<Candidate[]>(endpoint);
}

/**
 * Get a single candidate by ID
 */
export async function getCandidate(id: number): Promise<Candidate> {
  return fetchAPI<Candidate>(`/records/${id}`);
}

/**
 * Create a new candidate
 */
export async function createCandidate(data: CandidateFormData): Promise<Candidate> {
  const payload = {
    ...data,
    application_date: new Date().toISOString().split('T')[0], // Today's date in YYYY-MM-DD
  };

  return fetchAPI<Candidate>('/records', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Update an existing candidate (full update)
 */
export async function updateCandidate(
  id: number,
  data: Partial<CandidateFormData>
): Promise<Candidate> {
  return fetchAPI<Candidate>(`/records/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

/**
 * Update only the candidate's status
 */
export async function updateCandidateStatus(
  id: number,
  status: Status
): Promise<{ message: string; status: Status }> {
  return fetchAPI(`/records/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}

/**
 * Update only the candidate's recruitment stage
 */
export async function updateCandidateStage(
  id: number,
  stage: Stage
): Promise<{ message: string; stage: Stage }> {
  return fetchAPI(`/records/${id}/stage`, {
    method: 'PATCH',
    body: JSON.stringify({ stage }),
  });
}

// ============ NOTES API ============

/**
 * Get all notes for a candidate
 */
export async function getNotes(candidateId: number): Promise<Note[]> {
  return fetchAPI<Note[]>(`/records/${candidateId}/notes`);
}

/**
 * Create a new note for a candidate
 */
export async function createNote(
  candidateId: number,
  data: NoteFormData
): Promise<Note> {
  return fetchAPI<Note>(`/records/${candidateId}/notes`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Delete a note
 */
export async function deleteNote(
  candidateId: number,
  noteId: number
): Promise<void> {
  return fetchAPI<void>(`/records/${candidateId}/notes/${noteId}`, {
    method: 'DELETE',
  });
}

// ============ HEALTH CHECK ============

/**
 * Check if API is healthy
 */
export async function healthCheck(): Promise<{ status: string }> {
  return fetchAPI<{ status: string }>('/health');
}

// ============ PASSWORD MANAGEMENT API (Hito 6 - AUTH-03) ============

export interface MessageResponse {
  message: string;
}

/**
 * Request password reset email
 * Always returns same message (anti-enumeration)
 */
export async function requestPasswordReset(email: string): Promise<MessageResponse> {
  return fetchAPI<MessageResponse>('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

/**
 * Reset password with token
 * Validates token and updates password
 */
export async function resetPassword(token: string, newPassword: string): Promise<MessageResponse> {
  return fetchAPI<MessageResponse>('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({
      token,
      new_password: newPassword
    }),
  });
}

/**
 * Change password (authenticated user)
 * Requires valid JWT token
 */
export async function changePassword(
  currentPassword: string,
  newPassword: string
): Promise<MessageResponse> {
  return fetchAPI<MessageResponse>('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

// ============ AUTHENTICATION API ============

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  role?: 'admin' | 'manager' | 'user';
  name?: string;
  phone?: string;
  address?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: number;
  email: string;
  role: 'admin' | 'manager' | 'user';
  is_active: boolean;
  created_at: string;
  profile?: {
    id: number;
    user_id: number;
    name: string;
    phone: string;
    address: string;
  } | null;
}

/**
 * Login user and receive JWT token
 */
export async function login(credentials: LoginCredentials): Promise<AuthResponse> {
  return fetchAPI<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
}

/**
 * Register new user
 */
export async function register(data: RegisterData): Promise<User> {
  return fetchAPI<User>('/users', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Get current authenticated user
 * Requires valid JWT token
 */
export async function getCurrentUser(): Promise<User> {
  return fetchAPI<User>('/auth/me');
}

/**
 * Update user profile (name, phone, address)
 * Requires valid JWT token
 */
export async function updateProfile(data: {
  name?: string;
  phone?: string;
  address?: string;
}): Promise<User> {
  return fetchAPI<User>('/profiles/me', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// ============ INCIDENTS API (Fase 4) ============

export type IncidentStatus = 'open' | 'in_progress' | 'resolved' | 'discarded';
export type IncidentOrigin = 'customer' | 'branch' | 'internal';
export type IncidentCategory =
  | 'calidad_comida'
  | 'servicio_cliente'
  | 'operaciones'
  | 'infraestructura'
  | 'pedidos_online'
  | 'facturacion';
export type IncidentBranch =
  | 'medellin_centro' | 'medellin_poblado' | 'medellin_envigado'
  | 'bogota_zona_rosa' | 'bogota_usaquen' | 'bogota_suba'
  | 'cali_norte' | 'cali_sur'
  | 'cartagena_centro' | 'barranquilla_norte'
  | 'miami_beach' | 'miami_downtown'
  | 'orlando_international' | 'tampa_centro'
  | 'central';

export interface Incident {
  id: string;
  title: string;
  description: string;
  category: IncidentCategory;
  status: IncidentStatus;
  origin: IncidentOrigin;
  branch: IncidentBranch;
  created_at: string;
  updated_at: string;
  satisfaction?: number;
  legacy_id?: string;
}

export interface IncidentCreateData {
  title: string;
  description: string;
  category: IncidentCategory;
  origin: IncidentOrigin;
  branch: IncidentBranch;
}

export interface IncidentStatusUpdate {
  status: IncidentStatus;
  satisfaction?: number;
}

export interface IncidentFilters {
  status?: IncidentStatus;
  origin?: IncidentOrigin;
  branch?: IncidentBranch;
  category?: IncidentCategory;
  limit?: number;
  offset?: number;
}

export interface IncidentListResponse {
  total: number;
  items: Incident[];
  limit: number;
  offset: number;
}

export interface IncidentSummary {
  total_incidents: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_origin: Record<string, number>;
  by_branch: Record<string, number>;
  avg_satisfaction: number | null;
}

/**
 * Create new incident (starts as 'open')
 * Requires JWT authentication
 */
export async function createIncident(data: IncidentCreateData): Promise<Incident> {
  return fetchAPI<Incident>('/incidents', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * List incidents with optional filters
 * Requires JWT authentication
 */
export async function getIncidents(filters?: IncidentFilters): Promise<IncidentListResponse> {
  const params = new URLSearchParams();

  if (filters?.status) params.set('status', filters.status);
  if (filters?.origin) params.set('origin', filters.origin);
  if (filters?.branch) params.set('branch', filters.branch);
  if (filters?.category) params.set('category', filters.category);
  if (filters?.limit) params.set('limit', filters.limit.toString());
  if (filters?.offset) params.set('offset', filters.offset.toString());

  const queryString = params.toString();
  const endpoint = queryString ? `/incidents?${queryString}` : '/incidents';

  return fetchAPI<IncidentListResponse>(endpoint);
}

/**
 * Get incident detail by UUID
 * Requires JWT authentication
 */
export async function getIncident(id: string): Promise<Incident> {
  return fetchAPI<Incident>(`/incidents/${id}`);
}

/**
 * Update incident status (state machine validation)
 * Requires JWT authentication
 */
export async function updateIncidentStatus(
  id: string,
  data: IncidentStatusUpdate
): Promise<Incident> {
  return fetchAPI<Incident>(`/incidents/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Get aggregate metrics (summary)
 * Requires JWT authentication
 */
export async function getIncidentsSummary(): Promise<IncidentSummary> {
  return fetchAPI<IncidentSummary>('/incidents/summary');
}
