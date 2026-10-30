/**
 * React Hook - SSE Notifications for RFP Tickets
 *
 * Características:
 * - Consume SSE endpoint con fetch + ReadableStream (NO EventSource)
 * - Autenticación JWT via header Authorization
 * - Reconexión automática con backoff exponencial + jitter
 * - Deduplicación por ticket_id
 * - Sincronización al reconectar (refetch + SSE)
 *
 * CRÍTICO:
 * - NO usar EventSource nativa (no permite headers personalizados)
 * - Implementar backoff progresivo: 1s, 2s, 4s, 8s, 16s, 32s (max)
 * - Deduplicar tickets en memoria (Map<ticket_id, Ticket>)
 */

import { useEffect, useState, useCallback, useRef } from 'react';

// ============================================================
// TYPES
// ============================================================

export interface RFPTicket {
  ticket_id: number;
  status: string;
  filename: string;
  client_name?: string;
  created_at: string;
}

interface SSEEvent {
  type: string;
  data: string;
  id?: string;
}

interface UseRFPNotificationsOptions {
  apiBaseUrl?: string;
  autoConnect?: boolean;
  maxReconnectDelay?: number;  // Max delay en ms (default: 32000)
  onTicketCreated?: (ticket: RFPTicket) => void;
  onError?: (error: Error) => void;
}

interface UseRFPNotificationsReturn {
  tickets: RFPTicket[];
  isConnected: boolean;
  connectionError: Error | null;
  reconnectAttempts: number;
  connect: () => void;
  disconnect: () => void;
}

// ============================================================
// HOOK
// ============================================================

export function useRFPNotifications(
  jwtToken: string,
  options: UseRFPNotificationsOptions = {}
): UseRFPNotificationsReturn {
  const {
    apiBaseUrl = '/api',
    autoConnect = true,
    maxReconnectDelay = 32000,
    onTicketCreated,
    onError,
  } = options;

  // State
  const [tickets, setTickets] = useState<RFPTicket[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<Error | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  // Refs
  const abortControllerRef = useRef<AbortController | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const ticketsMapRef = useRef<Map<number, RFPTicket>>(new Map());

  // ============================================================
  // FETCH INITIAL TICKETS (Sincronización al reconectar)
  // ============================================================

  const fetchInitialTickets = useCallback(async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/rfp/tickets?limit=20`, {
        headers: {
          'Authorization': `Bearer ${jwtToken}`,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const fetchedTickets: RFPTicket[] = data.tickets || [];

      // Actualizar mapa de tickets (deduplicación)
      fetchedTickets.forEach(ticket => {
        ticketsMapRef.current.set(ticket.ticket_id, ticket);
      });

      // Actualizar estado
      setTickets(Array.from(ticketsMapRef.current.values()));

      console.log(`[SSE] Sincronizados ${fetchedTickets.length} tickets`);
    } catch (error) {
      console.error('[SSE] Error fetching initial tickets:', error);
      // NO lanzar error: continuar con SSE aunque falle el refetch
    }
  }, [apiBaseUrl, jwtToken]);

  // ============================================================
  // CONNECT SSE
  // ============================================================

  const connectSSE = useCallback(async () => {
    // Cancelar conexión anterior si existe
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Crear nuevo AbortController
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const url = `${apiBaseUrl}/notifications/sse`;

    console.log(`[SSE] Conectando a ${url}...`);

    try {
      // Fetch con headers personalizados
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${jwtToken}`,
          'Accept': 'text/event-stream',
        },
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Conexión exitosa
      setIsConnected(true);
      setConnectionError(null);
      setReconnectAttempts(0);

      console.log('[SSE] Conexión establecida');

      // Leer stream con TextDecoder
      const reader = response.body!
        .pipeThrough(new TextDecoderStream())
        .getReader();

      let buffer = '';

      // Loop de lectura
      while (true) {
        const { value, done } = await reader.read();

        if (done) {
          console.log('[SSE] Stream terminado por servidor');
          break;
        }

        buffer += value;

        // Parsear eventos SSE (separados por \n\n)
        const parts = buffer.split('\n\n');
        buffer = parts.pop()!; // Último fragmento incompleto

        for (const eventBlock of parts) {
          if (!eventBlock.trim()) continue;

          // Ignorar comentarios keep-alive
          if (eventBlock.startsWith(':')) {
            console.log('[SSE] Keep-alive recibido');
            continue;
          }

          const event = parseSSEEvent(eventBlock);

          // Procesar evento
          if (event.type === 'rfp_ticket_created') {
            try {
              const ticket: RFPTicket = JSON.parse(event.data);

              // Deduplicación
              if (!ticketsMapRef.current.has(ticket.ticket_id)) {
                ticketsMapRef.current.set(ticket.ticket_id, ticket);

                // Actualizar estado (insertar al tope)
                setTickets(Array.from(ticketsMapRef.current.values()));

                console.log(`[SSE] Nuevo ticket: ${ticket.ticket_id}`);

                // Callback
                if (onTicketCreated) {
                  onTicketCreated(ticket);
                }
              } else {
                console.log(`[SSE] Ticket duplicado ignorado: ${ticket.ticket_id}`);
              }
            } catch (err) {
              console.error('[SSE] Error parseando evento:', err);
            }
          } else if (event.type === 'connected') {
            console.log('[SSE] Evento de conexión:', event.data);
          }
        }
      }

      // Stream cerrado normalmente
      setIsConnected(false);
      scheduleReconnect();
    } catch (error: any) {
      // Error en conexión
      if (error.name === 'AbortError') {
        console.log('[SSE] Conexión abortada manualmente');
        return;
      }

      console.error('[SSE] Error de conexión:', error);

      setIsConnected(false);
      setConnectionError(error);

      if (onError) {
        onError(error);
      }

      // Programar reconexión
      scheduleReconnect();
    }
  }, [apiBaseUrl, jwtToken, onTicketCreated, onError]);

  // ============================================================
  // RECONNECT WITH BACKOFF
  // ============================================================

  const scheduleReconnect = useCallback(() => {
    // Incrementar contador
    setReconnectAttempts((prev) => {
      const newAttempts = prev + 1;

      // Calcular delay con backoff exponencial
      const baseDelay = 1000; // 1 segundo
      const exponentialDelay = baseDelay * Math.pow(2, Math.min(newAttempts - 1, 5)); // Max 2^5 = 32s
      const cappedDelay = Math.min(exponentialDelay, maxReconnectDelay);

      // Jitter: ±20%
      const jitter = cappedDelay * 0.2 * (Math.random() - 0.5);
      const finalDelay = cappedDelay + jitter;

      console.log(
        `[SSE] Reconectando en ${(finalDelay / 1000).toFixed(1)}s (intento ${newAttempts})...`
      );

      // Programar reconexión
      reconnectTimeoutRef.current = window.setTimeout(() => {
        // Refetch inicial antes de reconectar SSE
        fetchInitialTickets().then(() => {
          connectSSE();
        });
      }, finalDelay);

      return newAttempts;
    });
  }, [connectSSE, fetchInitialTickets, maxReconnectDelay]);

  // ============================================================
  // CONNECT / DISCONNECT
  // ============================================================

  const connect = useCallback(() => {
    // Fetch inicial + SSE
    fetchInitialTickets().then(() => {
      connectSSE();
    });
  }, [fetchInitialTickets, connectSSE]);

  const disconnect = useCallback(() => {
    console.log('[SSE] Desconectando...');

    // Abortar fetch
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Cancelar timeout de reconexión
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    setIsConnected(false);
    setReconnectAttempts(0);
  }, []);

  // ============================================================
  // EFFECTS
  // ============================================================

  useEffect(() => {
    if (autoConnect && jwtToken) {
      connect();
    }

    // Cleanup
    return () => {
      disconnect();
    };
  }, [autoConnect, jwtToken]); // Solo reconectar si cambia el token

  return {
    tickets,
    isConnected,
    connectionError,
    reconnectAttempts,
    connect,
    disconnect,
  };
}

// ============================================================
// SSE PARSER
// ============================================================

function parseSSEEvent(block: string): SSEEvent {
  const lines = block.split('\n');
  const event: SSEEvent = { type: 'message', data: '' };

  for (const line of lines) {
    if (line.startsWith('event:')) {
      event.type = line.substring(6).trim();
    } else if (line.startsWith('data:')) {
      const dataLine = line.substring(5).trim();
      event.data += (event.data ? '\n' : '') + dataLine;
    } else if (line.startsWith('id:')) {
      event.id = line.substring(3).trim();
    }
  }

  return event;
}
