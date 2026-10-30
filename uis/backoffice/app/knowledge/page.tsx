"use client";

import { useState } from "react";
import { Send, BookOpen, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";

/**
 * Página de Consulta de Base de Conocimiento (RAG)
 *
 * Funcionalidades:
 * - Input de texto para preguntas
 * - Llamada a API /knowledge/query
 * - Visualización de respuesta
 * - Estados de carga/error
 * - Soporte light/dark mode
 * - Ejemplos de preguntas sugeridas
 */

interface QueryResponse {
  answer: string;
  question: string;
}

export default function KnowledgeBasePage() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [queryHistory, setQueryHistory] = useState<Array<{ question: string; answer: string }>>([]);

  // Preguntas sugeridas
  const suggestedQuestions = [
    "¿Cuántos locales tiene Brasaland y en qué países?",
    "¿Quién es el CEO de Brasaland?",
    "¿Cuáles son los horarios de apertura en Colombia?",
    "¿Qué sistemas técnicos tiene implementados Brasaland Digital?",
    "¿Cuál es la política de vacaciones en Estados Unidos?",
    "¿Cuántos empleados tiene Brasaland?",
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!question.trim()) {
      setError("Por favor ingresa una pregunta");
      return;
    }

    setIsLoading(true);
    setError(null);
    setAnswer(null);

    try {
      const response = await fetch("http://localhost:8000/knowledge/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Error al consultar la base de conocimiento");
      }

      const data: QueryResponse = await response.json();
      setAnswer(data.answer);

      // Agregar a historial
      setQueryHistory(prev => [{ question: data.question, answer: data.answer }, ...prev]);

      // Limpiar input
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconocido");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestedQuestion = (suggestedQuestion: string) => {
    setQuestion(suggestedQuestion);
  };

  const clearHistory = () => {
    setQueryHistory([]);
    setAnswer(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <BookOpen className="w-10 h-10 text-primary" />
            <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
              Base de Conocimiento
            </h1>
          </div>
          <p className="text-gray-600 dark:text-gray-400">
            Pregunta sobre Brasaland, sus operaciones, políticas y sistemas técnicos
          </p>
        </div>

        {/* Formulario de consulta */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="question" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Tu pregunta
              </label>
              <div className="flex gap-2">
                <input
                  id="question"
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Ej: ¿Cuántos locales tiene Brasaland?"
                  className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  disabled={isLoading || !question.trim()}
                  className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Consultando...
                    </>
                  ) : (
                    <>
                      <Send className="w-5 h-5" />
                      Preguntar
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Preguntas sugeridas */}
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Preguntas sugeridas:</p>
              <div className="flex flex-wrap gap-2">
                {suggestedQuestions.map((sq, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSuggestedQuestion(sq)}
                    className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                    disabled={isLoading}
                  >
                    {sq}
                  </button>
                ))}
              </div>
            </div>
          </form>
        </div>

        {/* Mensajes de estado */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-800 dark:text-red-300">Error</h3>
              <p className="text-red-700 dark:text-red-400">{error}</p>
            </div>
          </div>
        )}

        {/* Respuesta actual */}
        {answer && !error && (
          <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-6 mb-6">
            <div className="flex items-start gap-3 mb-4">
              <CheckCircle2 className="w-6 h-6 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
              <h3 className="text-lg font-semibold text-green-800 dark:text-green-300">Respuesta</h3>
            </div>
            <div className="prose dark:prose-invert max-w-none">
              <p className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed">
                {answer}
              </p>
            </div>
          </div>
        )}

        {/* Historial de consultas */}
        {queryHistory.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Historial de Consultas
              </h2>
              <button
                onClick={clearHistory}
                className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                Limpiar historial
              </button>
            </div>

            <div className="space-y-4">
              {queryHistory.map((item, idx) => (
                <div
                  key={idx}
                  className="border-l-4 border-primary pl-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <p className="font-medium text-gray-900 dark:text-white mb-2">
                    Q: {item.question}
                  </p>
                  <p className="text-gray-600 dark:text-gray-400 text-sm">
                    A: {item.answer.substring(0, 200)}
                    {item.answer.length > 200 && "..."}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Estado vacío */}
        {!answer && !error && !isLoading && queryHistory.length === 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
            <BookOpen className="w-16 h-16 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              ¿Tienes alguna pregunta sobre Brasaland?
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Escribe tu pregunta arriba o selecciona una de las sugerencias
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
