/**
 * React Hook - WebSocket Chat con Token Streaming
 *
 * DOMINIO: Brasaland Digital - Agente de Soporte
 *
 * CARACTERÍSTICAS:
 * - WebSocket bidireccional (envío + recepción concurrentes)
 * - Token streaming en tiempo real
 * - Abort de generación en curso
 * - Preservación de mensajes interrumpidos con distintivo [Interrumpido]
 * - Reconexión resiliente con rehidratación de historial
 * - Autenticación JWT via query string
 *
 * DIFERENCIAS CON useIncidentNotifications (SSE):
 * - SSE: Unidireccional (servidor → cliente)
 * - WebSocket: Bidireccional (cliente ↔ servidor)
 * - SSE: Solo recibir notificaciones
 * - WebSocket: Enviar mensajes + recibir respuestas
 */

import { useEffect, useState, useCallback, useRef } from 'react';

// ============================================================
// TYPES
// ============================================================

export interface ChatMessage {
  message_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  status: 'streaming' | 'completed' | 'interrupted';
  created_at: string;
}

export type WebSocketStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error';

export type GenerationStatus =
  | 'idle'        // Sin generación activa
  | 'generating'  // Generando respuesta
  | 'interrupted' // Generación interrumpida
  | 'completed';  // Generación completada

interface UseChatWebSocketOptions {
  apiBaseUrl?: string;
  autoConnect?: boolean;
  maxReconnectDelay?: number;
  onMessageReceived?: (message: ChatMessage) => void;
  onError?: (error: Error) => void;
}

interface UseChatWebSocketReturn {
  messages: ChatMessage[];
  status: WebSocketStatus;
  generationStatus: GenerationStatus;
  reconnectAttempts: number;
  sendMessage: (content: string) => void;
  abortGeneration: () => void;
  connect: () => void;
  disconnect: () => void;
}

// ============================================================
// HOOK
// ============================================================

export function useChatWebSocket(
  sessionId: string,
  jwtToken: string,
  options: UseChatWebSocketOptions = {}
): UseChatWebSocketReturn {
  const {
    apiBaseUrl = '/api',
    autoConnect = true,
    maxReconnectDelay = 32000,
    onMessageReceived,
    onError,
  } = options;

  // State
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus>('idle');
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const currentMessageRef = useRef<ChatMessage | null>(null);

  // ============================================================
  // CONNECT WEBSOCKET
  // ============================================================

  const connectWS = useCallback(() => {
    // Cancelar reconexión pendiente
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Construir URL WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}${apiBaseUrl}/ws/chat/${sessionId}?token=${jwtToken}`;

    console.log(`[WS] Conectando a ${wsUrl.replace(jwtToken, 'TOKEN')}...`);

    setStatus('connecting');

    try {
      // Crear WebSocket
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      // ============================================================
      // EVENT LISTENERS
      // ============================================================

      ws.onopen = () => {
        console.log('[WS] Conexión establecida');
        setStatus('connected');
        setReconnectAttempts(0);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleServerMessage(data);
        } catch (err) {
          console.error('[WS] Error parseando mensaje:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('[WS] Error de WebSocket:', error);
        setStatus('error');

        if (onError) {
          onError(new Error('WebSocket connection error'));
        }
      };

      ws.onclose = (event) => {
        console.log(`[WS] Conexión cerrada (código ${event.code})`);
        setStatus('disconnected');
        wsRef.current = null;

        // Reconectar automáticamente (excepto cierre normal)
        if (event.code !== 1000 && autoConnect) {
          scheduleReconnect();
        }
      };
    } catch (error) {
      console.error('[WS] Error creando WebSocket:', error);
      setStatus('error');

      if (onError) {
        onError(error as Error);
      }
    }
  }, [sessionId, jwtToken, apiBaseUrl, autoConnect, onError]);

  // ============================================================
  // HANDLE SERVER MESSAGES
  // ============================================================

  function handleServerMessage(data: any) {
    const { type } = data;

    switch (type) {
      case 'history':
        // Rehidratación: Cargar historial completo
        console.log(`[WS] Historial recibido: ${data.messages.length} mensajes`);
        setMessages(data.messages);
        break;

      case 'token_chunk':
        // Token streaming: Acumular en mensaje actual
        handleTokenChunk(data);
        break;

      case 'generation_completed':
        // Generación completada
        handleGenerationCompleted(data);
        break;

      case 'generation_interrupted':
        // Generación interrumpida
        handleGenerationInterrupted(data);
        break;

      case 'error':
        // Error del servidor
        console.error('[WS] Error del servidor:', data.message);
        setGenerationStatus('idle');
        break;

      default:
        console.warn('[WS] Tipo de mensaje desconocido:', type);
    }
  }

  function handleTokenChunk(data: any) {
    const { delta, message_id } = data;

    setGenerationStatus('generating');

    setMessages((prev) => {
      // Buscar mensaje existente
      const existingIndex = prev.findIndex(
        (msg) => msg.message_id === message_id
      );

      if (existingIndex !== -1) {
        // Actualizar mensaje existente (acumular delta)
        const updated = [...prev];
        updated[existingIndex] = {
          ...updated[existingIndex],
          content: updated[existingIndex].content + delta,
          status: 'streaming',
        };
        currentMessageRef.current = updated[existingIndex];
        return updated;
      } else {
        // Crear nuevo mensaje
        const newMessage: ChatMessage = {
          message_id,
          role: 'assistant',
          content: delta,
          status: 'streaming',
          created_at: new Date().toISOString(),
        };
        currentMessageRef.current = newMessage;
        return [...prev, newMessage];
      }
    });
  }

  function handleGenerationCompleted(data: any) {
    const { message_id } = data;

    console.log(`[WS] Generación completada: ${message_id}`);
    setGenerationStatus('completed');

    // Marcar mensaje como completado
    setMessages((prev) =>
      prev.map((msg) =>
        msg.message_id === message_id
          ? { ...msg, status: 'completed' as const }
          : msg
      )
    );

    currentMessageRef.current = null;

    // Resetear a idle después de 500ms
    setTimeout(() => {
      setGenerationStatus('idle');
    }, 500);
  }

  function handleGenerationInterrupted(data: any) {
    const { message_id, reason } = data;

    console.log(`[WS] Generación interrumpida: ${message_id} (${reason})`);
    setGenerationStatus('interrupted');

    // Marcar mensaje como interrumpido
    setMessages((prev) =>
      prev.map((msg) =>
        msg.message_id === message_id
          ? { ...msg, status: 'interrupted' as const }
          : msg
      )
    );

    currentMessageRef.current = null;

    // Resetear a idle después de 500ms
    setTimeout(() => {
      setGenerationStatus('idle');
    }, 500);
  }

  // ============================================================
  // SEND MESSAGE
  // ============================================================

  const sendMessage = useCallback(
    (content: string) => {
      const ws = wsRef.current;

      if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.error('[WS] No se puede enviar mensaje: WebSocket no conectado');
        return;
      }

      // Generar message_id
      const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

      // Agregar mensaje del usuario inmediatamente (optimistic update)
      const userMessage: ChatMessage = {
        message_id: messageId,
        role: 'user',
        content,
        status: 'completed',
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);

      // Enviar al servidor
      ws.send(
        JSON.stringify({
          type: 'user_message',
          content,
          message_id: messageId,
        })
      );

      console.log(`[WS] Mensaje enviado: ${content.substring(0, 50)}...`);
    },
    []
  );

  // ============================================================
  // ABORT GENERATION
  // ============================================================

  const abortGeneration = useCallback(() => {
    const ws = wsRef.current;

    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.error('[WS] No se puede abortar: WebSocket no conectado');
      return;
    }

    // Enviar señal de abort
    ws.send(
      JSON.stringify({
        type: 'abort',
      })
    );

    console.log('[WS] Señal de abort enviada');
  }, []);

  // ============================================================
  // RECONNECT WITH BACKOFF
  // ============================================================

  const scheduleReconnect = useCallback(() => {
    setStatus('reconnecting');

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
        `[WS] Reconectando en ${(finalDelay / 1000).toFixed(1)}s (intento ${newAttempts})...`
      );

      reconnectTimeoutRef.current = window.setTimeout(() => {
        connectWS();
      }, finalDelay);

      return newAttempts;
    });
  }, [connectWS, maxReconnectDelay]);

  // ============================================================
  // CONNECT / DISCONNECT
  // ============================================================

  const connect = useCallback(() => {
    connectWS();
  }, [connectWS]);

  const disconnect = useCallback(() => {
    console.log('[WS] Desconectando...');

    // Cancelar reconexión
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Cerrar WebSocket
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setStatus('disconnected');
    setReconnectAttempts(0);
  }, []);

  // ============================================================
  // EFFECTS
  // ============================================================

  useEffect(() => {
    if (autoConnect && sessionId && jwtToken) {
      connect();
    }

    // Cleanup
    return () => {
      disconnect();
    };
  }, [autoConnect, sessionId, jwtToken]);

  return {
    messages,
    status,
    generationStatus,
    reconnectAttempts,
    sendMessage,
    abortGeneration,
    connect,
    disconnect,
  };
}
