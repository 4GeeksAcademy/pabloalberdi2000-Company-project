/**
 * React Hook - SSE Notifications for Brasaland Incidents
 *
 * DOMINIO: Sistema de Análisis de Incidencias Postventa
 * Usuario: Operaciones + Dirección
 * Locales: 14 restaurantes (10 CO + 4 US)
 *
 * Características:
 * - Consume SSE endpoint con fetch + ReadableStream
 * - Autenticación JWT via header Authorization
 * - Reconexión automática con backoff exponencial + jitter
 * - Deduplicación por incident_id con persistencia localStorage
 * - Sincronización al reconectar (refetch + SSE)
 */

import { useEffect, useState, useCallback, useRef } from 'react';

// ============================================================
// TYPES - BRASALAND DOMAIN
// ============================================================

export interface BrasalandIncident {
  incident_id: number;
  local_name: string;        // "Medellín Centro", "Miami Beach", "Bogotá Norte"
  country: string;           // "CO" | "US"
  category: string;          // "calidad_comida", "servicio", "tiempo_espera", "higiene", "ambiente"
  severity: string;          // "baja", "media", "alta", "critica"
  description: string;
  customer_name?: string;
  created_at: string;
}

interface SSEEvent {
  type: string;
  data: string;
  id?: string;
}

interface UseIncidentNotificationsOptions {
  apiBaseUrl?: string;
  autoConnect?: boolean;
  maxReconnectDelay?: number;
  onIncidentCreated?: (incident: BrasalandIncident) => void;
  onError?: (error: Error) => void;
}

interface UseIncidentNotificationsReturn {
  incidents: BrasalandIncident[];
  isConnected: boolean;
  connectionError: Error | null;
  reconnectAttempts: number;
  connect: () => void;
  disconnect: () => void;
}

// ============================================================
// HOOK
// ============================================================

export function useIncidentNotifications(
  jwtToken: string,
  options: UseIncidentNotificationsOptions = {}
): UseIncidentNotificationsReturn {
  const {
    apiBaseUrl = '/api',
    autoConnect = true,
    maxReconnectDelay = 32000,
    onIncidentCreated,
    onError,
  } = options;

  // State
  const [incidents, setIncidents] = useState<BrasalandIncident[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<Error | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  // Refs
  const abortControllerRef = useRef<AbortController | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const incidentsMapRef = useRef<Map<number, BrasalandIncident>>(new Map());

  // ============================================================
  // PERSISTENCIA LOCALSTORAGE (Fix Criterio 2)
  // ============================================================

  useEffect(() => {
    // Cargar historial visto al montar
    try {
      const stored = localStorage.getItem('brasaland_incidents_seen');
      if (stored) {
        const parsed = JSON.parse(stored);
        incidentsMapRef.current = new Map(Object.entries(parsed).map(
          ([id, incident]) => [parseInt(id), incident as BrasalandIncident]
        ));
        setIncidents(Array.from(incidentsMapRef.current.values()));
        console.log(`[SSE] Cargados ${incidentsMapRef.current.size} incidentes desde localStorage`);
      }
    } catch (error) {
      console.error('[SSE] Error cargando localStorage:', error);
    }
  }, []);

  useEffect(() => {
    // Persistir al actualizar
    if (incidents.length > 0) {
      try {
        const obj = Object.fromEntries(incidentsMapRef.current);
        localStorage.setItem('brasaland_incidents_seen', JSON.stringify(obj));
      } catch (error) {
        console.error('[SSE] Error guardando localStorage:', error);
      }
    }
  }, [incidents]);

  // ============================================================
  // FETCH INITIAL INCIDENTS
  // ============================================================

  const fetchInitialIncidents = useCallback(async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/incidents?limit=20`, {
        headers: {
          'Authorization': `Bearer ${jwtToken}`,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const fetchedIncidents: BrasalandIncident[] = data.incidents || [];

      // Actualizar mapa (deduplicación)
      fetchedIncidents.forEach(incident => {
        incidentsMapRef.current.set(incident.incident_id, incident);
      });

      // Actualizar estado
      setIncidents(Array.from(incidentsMapRef.current.values()));

      console.log(`[SSE] Sincronizados ${fetchedIncidents.length} incidentes`);
    } catch (error) {
      console.error('[SSE] Error fetching initial incidents:', error);
      // NO lanzar: continuar con SSE aunque falle el refetch
    }
  }, [apiBaseUrl, jwtToken]);

  // ============================================================
  // CONNECT SSE
  // ============================================================

  const connectSSE = useCallback(async () => {
    // Cancelar conexión anterior
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    const url = `${apiBaseUrl}/notifications/sse`;

    console.log(`[SSE] Conectando a ${url}...`);

    try {
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

      // Leer stream
      const reader = response.body!
        .pipeThrough(new TextDecoderStream())
        .getReader();

      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();

        if (done) {
          console.log('[SSE] Stream terminado por servidor');
          break;
        }

        buffer += value;

        const parts = buffer.split('\n\n');
        buffer = parts.pop()!;

        for (const eventBlock of parts) {
          if (!eventBlock.trim()) continue;

          // Ignorar keep-alive
          if (eventBlock.startsWith(':')) {
            console.log('[SSE] Keep-alive recibido');
            continue;
          }

          const event = parseSSEEvent(eventBlock);

          // Procesar evento de incidencia
          if (event.type === 'incident_created') {
            try {
              const incident: BrasalandIncident = JSON.parse(event.data);

              // Deduplicación
              if (!incidentsMapRef.current.has(incident.incident_id)) {
                incidentsMapRef.current.set(incident.incident_id, incident);

                // Actualizar estado (insertar al tope)
                setIncidents(Array.from(incidentsMapRef.current.values()));

                console.log(`[SSE] Nueva incidencia: ${incident.incident_id} - ${incident.local_name} (${incident.severity})`);

                // Callback
                if (onIncidentCreated) {
                  onIncidentCreated(incident);
                }
              } else {
                console.log(`[SSE] Incidencia duplicada ignorada: ${incident.incident_id}`);
              }
            } catch (err) {
              console.error('[SSE] Error parseando evento:', err);
            }
          } else if (event.type === 'connected') {
            console.log('[SSE] Evento de conexión:', event.data);
          }
        }
      }

      // Stream cerrado
      setIsConnected(false);
      scheduleReconnect();
    } catch (error: any) {
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

      scheduleReconnect();
    }
  }, [apiBaseUrl, jwtToken, onIncidentCreated, onError]);

  // ============================================================
  // RECONNECT WITH BACKOFF + JITTER
  // ============================================================

  const scheduleReconnect = useCallback(() => {
    setReconnectAttempts((prev) => {
      const newAttempts = prev + 1;

      // Backoff exponencial
      const baseDelay = 1000;
      const exponentialDelay = baseDelay * Math.pow(2, Math.min(newAttempts - 1, 5));
      const cappedDelay = Math.min(exponentialDelay, maxReconnectDelay);

      // Jitter ±20%
      const jitter = cappedDelay * 0.2 * (Math.random() - 0.5);
      const finalDelay = cappedDelay + jitter;

      console.log(
        `[SSE] Reconectando en ${(finalDelay / 1000).toFixed(1)}s (intento ${newAttempts})...`
      );

      reconnectTimeoutRef.current = window.setTimeout(() => {
        fetchInitialIncidents().then(() => {
          connectSSE();
        });
      }, finalDelay);

      return newAttempts;
    });
  }, [connectSSE, fetchInitialIncidents, maxReconnectDelay]);

  // ============================================================
  // CONNECT / DISCONNECT
  // ============================================================

  const connect = useCallback(() => {
    fetchInitialIncidents().then(() => {
      connectSSE();
    });
  }, [fetchInitialIncidents, connectSSE]);

  const disconnect = useCallback(() => {
    console.log('[SSE] Desconectando...');

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

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

    return () => {
      disconnect();
    };
  }, [autoConnect, jwtToken]);

  return {
    incidents,
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
