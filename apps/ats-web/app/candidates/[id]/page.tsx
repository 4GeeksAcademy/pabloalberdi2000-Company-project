'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  getCandidate,
  updateCandidateStatus,
  updateCandidateStage,
  getNotes,
  createNote,
  deleteNote,
} from '@/lib/api';
import type { Candidate, Note, Status, Stage } from '@/types';
import { STATUS_LABELS, STAGE_LABELS, COUNTRY_LABELS } from '@/types';

export default function CandidateDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const candidateId = parseInt(params.id);

  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [newNoteContent, setNewNoteContent] = useState('');
  const [noteAuthor, setNoteAuthor] = useState('');
  const [noteLoading, setNoteLoading] = useState(false);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [candidateData, notesData] = await Promise.all([
          getCandidate(candidateId),
          getNotes(candidateId),
        ]);
        setCandidate(candidateData);
        setNotes(notesData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Error desconocido');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [candidateId]);

  const handleStatusChange = async (newStatus: Status) => {
    if (!candidate) return;

    try {
      await updateCandidateStatus(candidateId, newStatus);
      setCandidate({ ...candidate, status: newStatus });
    } catch (err) {
      alert('Error al actualizar estado: ' + (err instanceof Error ? err.message : 'Error desconocido'));
    }
  };

  const handleStageChange = async (newStage: Stage) => {
    if (!candidate) return;

    try {
      await updateCandidateStage(candidateId, newStage);
      setCandidate({ ...candidate, stage: newStage });
    } catch (err) {
      alert('Error al actualizar etapa: ' + (err instanceof Error ? err.message : 'Error desconocido'));
    }
  };

  const handleAddNote = async () => {
    if (!newNoteContent.trim() || !noteAuthor.trim()) {
      alert('Por favor completa todos los campos de la nota');
      return;
    }

    setNoteLoading(true);
    try {
      const note = await createNote(candidateId, {
        content: newNoteContent,
        author: noteAuthor,
      });
      setNotes([note, ...notes]); // Add to beginning (most recent first)
      setNewNoteContent('');
      // Don't clear author - likely same person adding multiple notes
    } catch (err) {
      alert('Error al crear nota: ' + (err instanceof Error ? err.message : 'Error desconocido'));
    } finally {
      setNoteLoading(false);
    }
  };

  const handleDeleteNote = async (noteId: number) => {
    if (!confirm('¿Estás seguro de que quieres eliminar esta nota?')) {
      return;
    }

    try {
      await deleteNote(candidateId, noteId);
      setNotes(notes.filter((n) => n.id !== noteId));
    } catch (err) {
      alert('Error al eliminar nota: ' + (err instanceof Error ? err.message : 'Error desconocido'));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-orange-600 border-r-transparent"></div>
          <p className="mt-4 text-sm text-amber-800">Cargando candidato...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <strong>Error:</strong> {error}
        </div>
        <Link
          href="/"
          className="mt-4 inline-block text-sm text-orange-600 hover:text-orange-700"
        >
          ← Volver al listado
        </Link>
      </div>
    );
  }

  if (!candidate) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <p className="text-amber-800">Candidato no encontrado</p>
        <Link
          href="/"
          className="mt-4 inline-block text-sm text-orange-600 hover:text-orange-700"
        >
          ← Volver al listado
        </Link>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <Link
        href="/"
        className="inline-block mb-6 text-sm text-orange-600 hover:text-orange-700 transition"
      >
        ← Volver al listado
      </Link>

      <div className="rounded-lg border border-amber-200 bg-white shadow-sm p-6">
        {/* Header */}
        <div className="border-b border-amber-100 pb-6 mb-6">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-2">
            <div>
              <h1 className="text-3xl font-bold text-amber-950">
                {candidate.full_name}
              </h1>
              <p className="text-amber-800 mt-2">
                {candidate.position} · {COUNTRY_LABELS[candidate.country]}
                {candidate.location_preference && ` · ${candidate.location_preference}`}
              </p>
            </div>
            <Link
              href={`/candidates/${candidateId}/edit`}
              className="rounded-lg bg-orange-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-600 focus:ring-offset-2 text-center"
            >
              ✏️ Editar Candidato
            </Link>
          </div>
        </div>

        {/* Info Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div>
            <label className="block text-sm font-semibold text-amber-900 mb-1">Email</label>
            <p className="text-amber-800">{candidate.email}</p>
          </div>
          <div>
            <label className="block text-sm font-semibold text-amber-900 mb-1">Teléfono</label>
            <p className="text-amber-800">{candidate.phone}</p>
          </div>
          <div>
            <label className="block text-sm font-semibold text-amber-900 mb-1">Años de experiencia</label>
            <p className="text-amber-800">{candidate.years_experience} años</p>
          </div>
          <div>
            <label className="block text-sm font-semibold text-amber-900 mb-1">Fecha de aplicación</label>
            <p className="text-amber-800">
              {new Date(candidate.application_date).toLocaleDateString('es-ES', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </p>
          </div>
          {candidate.linkedin_url && (
            <div>
              <label className="block text-sm font-semibold text-amber-900 mb-1">LinkedIn</label>
              <a
                href={candidate.linkedin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-orange-600 hover:text-orange-700 hover:underline"
              >
                Ver perfil →
              </a>
            </div>
          )}
          {candidate.cv_url && (
            <div>
              <label className="block text-sm font-semibold text-amber-900 mb-1">CV</label>
              <a
                href={candidate.cv_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-orange-600 hover:text-orange-700 hover:underline"
              >
                Descargar CV →
              </a>
            </div>
          )}
        </div>

        {/* Status and Stage Controls */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6 pt-6 border-t border-amber-100">
          <div>
            <label className="block text-sm font-semibold text-amber-900 mb-2">
              Estado
            </label>
            <select
              value={candidate.status}
              onChange={(e) => handleStatusChange(e.target.value as Status)}
              className="w-full rounded-lg border border-amber-300 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200"
            >
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-semibold text-amber-900 mb-2">
              Etapa del proceso
            </label>
            <select
              value={candidate.stage}
              onChange={(e) => handleStageChange(e.target.value as Stage)}
              className="w-full rounded-lg border border-amber-300 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200"
            >
              {Object.entries(STAGE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Notes Section */}
        <div className="border-t border-amber-100 pt-6">
          <h2 className="text-xl font-bold text-amber-950 mb-4">Notas</h2>

          {/* Add Note Form */}
          <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
            <input
              type="text"
              placeholder="Tu nombre"
              value={noteAuthor}
              onChange={(e) => setNoteAuthor(e.target.value)}
              className="w-full rounded-lg border border-amber-300 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200 mb-3"
            />
            <textarea
              placeholder="Escribe una nota sobre este candidato..."
              value={newNoteContent}
              onChange={(e) => setNewNoteContent(e.target.value)}
              className="w-full rounded-lg border border-amber-300 bg-white px-4 py-2.5 text-sm outline-none transition focus:border-orange-600 focus:ring-2 focus:ring-orange-200 mb-3"
              rows={3}
            />
            <button
              onClick={handleAddNote}
              disabled={noteLoading}
              className="rounded-lg bg-orange-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-orange-700 focus:outline-none focus:ring-2 focus:ring-orange-600 focus:ring-offset-2 disabled:opacity-50"
            >
              {noteLoading ? 'Agregando...' : 'Agregar Nota'}
            </button>
          </div>

          {/* Notes List */}
          <div className="space-y-3">
            {notes.length === 0 ? (
              <p className="text-sm text-amber-700 italic">No hay notas todavía. Agrega la primera nota arriba.</p>
            ) : (
              notes.map((note) => (
                <div
                  key={note.id}
                  className="rounded-lg border border-amber-200 bg-gray-50 p-4"
                >
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <span className="font-semibold text-amber-950">{note.author}</span>
                      <span className="text-xs text-amber-700 ml-2">
                        {new Date(note.created_at).toLocaleString('es-ES', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    <button
                      onClick={() => handleDeleteNote(note.id)}
                      className="text-red-600 hover:text-red-800 text-sm transition"
                    >
                      Eliminar
                    </button>
                  </div>
                  <p className="text-sm text-amber-900 whitespace-pre-wrap">{note.content}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
