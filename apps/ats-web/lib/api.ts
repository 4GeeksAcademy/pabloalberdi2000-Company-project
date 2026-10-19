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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Generic fetch wrapper with error handling
 */
async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

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
