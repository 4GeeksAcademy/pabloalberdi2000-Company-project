/**
 * Utilidades para sanitización y manejo de errores
 *
 * Previene exposición de errores técnicos al usuario
 */

/**
 * Sanitiza un mensaje de error convirtiéndolo a lenguaje amigable
 */
export function sanitizeError(error: unknown): string {
  const errorMessage = error instanceof Error ? error.message : String(error);

  // Mapear errores técnicos a mensajes amigables
  if (errorMessage.includes('404') || errorMessage.toLowerCase().includes('not found')) {
    return 'El recurso solicitado no existe o fue eliminado';
  }

  if (errorMessage.includes('500') || errorMessage.toLowerCase().includes('internal server error')) {
    return 'Error del servidor. Por favor intenta más tarde';
  }

  if (errorMessage.includes('503') || errorMessage.toLowerCase().includes('service unavailable')) {
    return 'Servicio temporalmente no disponible. Intenta en unos minutos';
  }

  if (errorMessage.toLowerCase().includes('network') || errorMessage.toLowerCase().includes('fetch failed')) {
    return 'Error de conexión. Verifica tu red e intenta nuevamente';
  }

  if (errorMessage.toLowerCase().includes('timeout')) {
    return 'La solicitud tardó demasiado. Por favor intenta nuevamente';
  }

  if (errorMessage.toLowerCase().includes('unauthorized') || errorMessage.includes('401')) {
    return 'Tu sesión expiró. Por favor inicia sesión nuevamente';
  }

  if (errorMessage.toLowerCase().includes('forbidden') || errorMessage.includes('403')) {
    return 'No tienes permisos para realizar esta acción';
  }

  if (errorMessage.includes('422') || errorMessage.toLowerCase().includes('validation')) {
    return 'Los datos proporcionados son inválidos. Verifica e intenta nuevamente';
  }

  // Si el mensaje ya es amigable (no contiene stack traces, paths, o código técnico), retornarlo
  if (!containsTechnicalInfo(errorMessage)) {
    return errorMessage;
  }

  // Mensaje genérico por defecto
  return 'Ocurrió un error inesperado. Contacta a soporte si persiste';
}

/**
 * Detecta si un mensaje contiene información técnica que no debe mostrarse
 */
function containsTechnicalInfo(message: string): boolean {
  const technicalPatterns = [
    /at\s+\w+/i,           // Stack traces: "at Function"
    /\/(usr|var|home)\//i, // Paths absolutos
    /\w+Error:/i,          // Nombres de errores JS: "TypeError:"
    /line\s+\d+/i,         // Números de línea: "line 42"
    /\.tsx?:\d+/i,         // Archivos TS/TSX con líneas
    /\.py:\d+/i,           // Archivos Python con líneas
    /traceback/i,          // Stack traces Python
    /SQL/i,                // Mensajes SQL
    /SELECT|INSERT|UPDATE|DELETE/i, // Queries SQL
  ];

  return technicalPatterns.some(pattern => pattern.test(message));
}

/**
 * Obtiene un valor seguro con fallback para prevenir undefined
 */
export function safeGet<T>(value: T | null | undefined, fallback: T): T {
  return value ?? fallback;
}
