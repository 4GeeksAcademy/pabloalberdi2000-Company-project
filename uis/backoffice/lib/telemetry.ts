/**
 * Telemetry Service - Event Tracking con Batching y Retries
 *
 * Servicio singleton para captura de eventos de telemetría según
 * el estándar Event Envelope aprobado en TELEMETRY_PLAN.md.
 *
 * Features:
 * - Batching: Acumula eventos en memoria y envía cada 10s o 20 eventos
 * - Retries: 3 intentos con backoff exponencial (1s, 2s, 4s)
 * - sendBeacon: Envía eventos pendientes al ocultar/cerrar pestaña
 * - Enriquecimiento automático: eventId, timestamp, sessionId, userId, requestId
 * - API única: track(eventType, properties) - prohibido fetch/axios disperso
 */

// ============================================================
// Types
// ============================================================

interface TelemetryEvent {
  eventId: string;
  timestamp: string;
  sessionId: string | null;
  userId: string | null;
  event_type: string;
  schemaVersion: string;
  requestId: string;
  properties: Record<string, unknown>;
}

interface TelemetryBatchRequest {
  events: TelemetryEvent[];
}

interface TelemetryBatchResponse {
  received: number;
  status: "success";
}

// ============================================================
// Configuration
// ============================================================

const CONFIG = {
  /** Endpoint de ingestion (se configura vía env var) */
  endpoint: process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT || "http://localhost:8000/telemetry/events",

  /** Enviar batch cada N segundos */
  flushIntervalMs: 10_000, // 10 segundos

  /** Enviar batch cuando acumule N eventos */
  batchSize: 20,

  /** Máximo de reintentos por batch fallido */
  maxRetries: 3,

  /** Backoff inicial en ms (se duplica exponencialmente) */
  initialBackoffMs: 1000, // 1s, 2s, 4s

  /** Schema version del Event Envelope */
  schemaVersion: "1.0.0",
} as const;

// ============================================================
// Utilities
// ============================================================

/** Genera UUID v4 */
function generateUUID(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback para navegadores antiguos
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/** Genera timestamp ISO 8601 UTC */
function generateTimestamp(): string {
  return new Date().toISOString();
}

/** Obtiene sessionId (generado al login, persistido en sessionStorage) */
function getSessionId(): string | null {
  if (typeof window === "undefined") return null;

  try {
    let sessionId = sessionStorage.getItem("telemetry_session_id");
    if (!sessionId) {
      sessionId = `sess_${generateUUID()}`;
      sessionStorage.setItem("telemetry_session_id", sessionId);
    }
    return sessionId;
  } catch {
    // sessionStorage bloqueado (private mode, permisos)
    return null;
  }
}

/** Obtiene userId desde el estado de autenticación */
function getUserId(): string | null {
  if (typeof window === "undefined") return null;

  try {
    // TODO: Integrar con hook useAuth() o contexto de auth
    // Por ahora busca en localStorage donde el sistema auth guarda el token
    const token = localStorage.getItem("token");
    if (!token) return null;

    // Decodificar JWT payload (sin validar signature, solo lectura)
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.sub || payload.user_id || null;
  } catch {
    return null;
  }
}

/** Genera requestId para correlación */
function generateRequestId(): string {
  return `req_${generateUUID()}`;
}

/** Sleep con Promise (para backoff) */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ============================================================
// Telemetry Service
// ============================================================

class TelemetryService {
  private queue: TelemetryEvent[] = [];
  private flushTimer: NodeJS.Timeout | null = null;
  private isInitialized = false;

  constructor() {
    if (typeof window !== "undefined") {
      this.initialize();
    }
  }

  /**
   * Inicializa el servicio (solo en browser).
   * - Configura temporizador de flush automático
   * - Registra listener de visibilitychange para sendBeacon
   */
  private initialize(): void {
    if (this.isInitialized) return;
    this.isInitialized = true;

    // Timer de flush automático cada 10s
    this.flushTimer = setInterval(() => {
      this.flush();
    }, CONFIG.flushIntervalMs);

    // Flush al ocultar/cerrar pestaña con sendBeacon
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") {
        this.flushWithBeacon();
      }
    });

    // Cleanup al descargar página
    window.addEventListener("beforeunload", () => {
      this.flushWithBeacon();
    });

    console.log("📊 TelemetryService initialized");
  }

  /**
   * API pública: Captura un evento de telemetría.
   *
   * IMPORTANTE: Esta es la ÚNICA función pública permitida.
   * Queda prohibido hacer fetch/axios directos desde componentes.
   *
   * @param eventType - Tipo de evento en formato entidad_acción (snake_case)
   * @param properties - Payload específico del evento
   *
   * @example
   * ```typescript
   * track("page_view", {
   *   page_name: "inventory_ingredients",
   *   referrer: document.referrer
   * });
   * ```
   */
  track(eventType: string, properties: Record<string, unknown>): void {
    if (typeof window === "undefined") {
      // SSR: no trackear en servidor
      return;
    }

    const event: TelemetryEvent = {
      eventId: generateUUID(),
      timestamp: generateTimestamp(),
      sessionId: getSessionId(),
      userId: getUserId(),
      event_type: eventType,
      schemaVersion: CONFIG.schemaVersion,
      requestId: generateRequestId(),
      properties,
    };

    this.queue.push(event);

    // Flush automático si alcanza batchSize
    if (this.queue.length >= CONFIG.batchSize) {
      this.flush();
    }
  }

  /**
   * Envía eventos pendientes a la API con reintentos.
   * Llamado automáticamente por timer o cuando queue alcanza batchSize.
   */
  private async flush(): Promise<void> {
    if (this.queue.length === 0) return;

    const batch = [...this.queue];
    this.queue = []; // Vaciar cola inmediatamente

    await this.sendBatchWithRetries(batch);
  }

  /**
   * Envía eventos pendientes usando navigator.sendBeacon.
   * Garantiza envío incluso si la página se cierra/oculta.
   * No usa reintentos (sendBeacon es fire-and-forget).
   */
  private flushWithBeacon(): void {
    if (this.queue.length === 0) return;

    const batch = [...this.queue];
    this.queue = [];

    const payload: TelemetryBatchRequest = { events: batch };
    const blob = new Blob([JSON.stringify(payload)], {
      type: "application/json",
    });

    try {
      const sent = navigator.sendBeacon(CONFIG.endpoint, blob);
      if (sent) {
        console.log(`📤 sendBeacon: ${batch.length} events`);
      } else {
        console.warn(`⚠️ sendBeacon failed (queue full)`);
      }
    } catch (error) {
      console.error("❌ sendBeacon error:", error);
    }
  }

  /**
   * Envía batch con reintentos y backoff exponencial.
   *
   * @param batch - Lote de eventos a enviar
   * @param attempt - Intento actual (interno)
   */
  private async sendBatchWithRetries(
    batch: TelemetryEvent[],
    attempt = 1
  ): Promise<void> {
    try {
      const response = await fetch(CONFIG.endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ events: batch } as TelemetryBatchRequest),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result: TelemetryBatchResponse = await response.json();
      console.log(`✅ Telemetry sent: ${result.received} events`);
    } catch (error) {
      console.error(
        `❌ Telemetry send failed (attempt ${attempt}/${CONFIG.maxRetries}):`,
        error
      );

      // Reintentar con backoff exponencial
      if (attempt < CONFIG.maxRetries) {
        const backoffMs = CONFIG.initialBackoffMs * Math.pow(2, attempt - 1);
        console.log(`⏳ Retrying in ${backoffMs}ms...`);
        await sleep(backoffMs);
        await this.sendBatchWithRetries(batch, attempt + 1);
      } else {
        console.warn(
          `⚠️ Telemetry batch discarded after ${CONFIG.maxRetries} attempts`
        );
        // TODO (opcional): Guardar en localStorage para retry posterior
      }
    }
  }

  /**
   * Cleanup del servicio (destructor).
   * Llamado automáticamente al descargar página.
   */
  destroy(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
    this.flush(); // Último flush sincrónico
  }
}

// ============================================================
// Singleton Export
// ============================================================

/**
 * Instancia singleton del servicio de telemetría.
 *
 * @example
 * ```typescript
 * import { telemetry } from "@/lib/telemetry";
 *
 * telemetry.track("login_attempt_failed", {
 *   email_hash: "8d969eef...",
 *   failure_reason: "invalid_credentials"
 * });
 * ```
 */
export const telemetry = new TelemetryService();

/**
 * Alias para track() (sintaxis abreviada).
 *
 * @example
 * ```typescript
 * import { track } from "@/lib/telemetry";
 *
 * track("page_view", { page_name: "dashboard" });
 * ```
 */
export const track = telemetry.track.bind(telemetry);
