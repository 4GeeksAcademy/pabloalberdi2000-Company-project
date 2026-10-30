/**
 * React Component - Chat WebSocket con Token Streaming
 *
 * DOMINIO: Brasaland Digital - Agente de Soporte
 * Usuario: Equipo Interno
 *
 * CARACTERÍSTICAS:
 * - Renderizado progresivo de tokens (typing effect)
 * - Botón "Detener respuesta" durante generación
 * - Distintivo visual [Interrumpido] en mensajes parciales
 * - Reconexión con rehidratación automática
 * - Input siempre disponible (interrumpe generación si está activa)
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useChatWebSocket, ChatMessage } from '../hooks/useChatWebSocket';

// ============================================================
// TYPES
// ============================================================

interface ChatWebSocketProps {
  sessionId: string;
  jwtToken: string;
  onClose?: () => void;
}

// ============================================================
// COMPONENT
// ============================================================

export function ChatWebSocket({
  sessionId,
  jwtToken,
  onClose,
}: ChatWebSocketProps) {
  // Hook WebSocket
  const {
    messages,
    status,
    generationStatus,
    reconnectAttempts,
    sendMessage,
    abortGeneration,
  } = useChatWebSocket(sessionId, jwtToken, {
    apiBaseUrl: '/api',
    autoConnect: true,
  });

  // State
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // ============================================================
  // AUTO-SCROLL
  // ============================================================

  useEffect(() => {
    // Scroll al final cuando llegan nuevos mensajes
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ============================================================
  // HANDLERS
  // ============================================================

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();

      const trimmed = inputValue.trim();
      if (!trimmed) return;

      // Enviar mensaje (abortará generación si está activa)
      sendMessage(trimmed);

      // Limpiar input
      setInputValue('');
    },
    [inputValue, sendMessage]
  );

  const handleAbort = useCallback(() => {
    abortGeneration();
  }, [abortGeneration]);

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="chat-websocket">
      {/* Header */}
      <div className="chat-websocket__header">
        <div className="chat-websocket__title">
          <h2>Asistente Brasaland</h2>
          <span className="chat-websocket__session">
            Sesión: {sessionId.substring(0, 8)}...
          </span>
        </div>

        <div className="chat-websocket__status-bar">
          {/* Estado WebSocket */}
          <div
            className={`chat-websocket__status chat-websocket__status--${status}`}
          >
            {status === 'connected' && '🟢 Conectado'}
            {status === 'connecting' && '🟡 Conectando...'}
            {status === 'reconnecting' &&
              `🟡 Reconectando... (${reconnectAttempts})`}
            {status === 'disconnected' && '🔴 Desconectado'}
            {status === 'error' && '🔴 Error'}
          </div>

          {/* Estado de generación */}
          {generationStatus === 'generating' && (
            <div className="chat-websocket__generation-status">
              ⏳ Generando...
            </div>
          )}

          {onClose && (
            <button
              className="chat-websocket__close-btn"
              onClick={onClose}
              aria-label="Cerrar chat"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="chat-websocket__messages">
        {messages.length === 0 ? (
          <div className="chat-websocket__empty">
            <p>👋 ¡Hola! Soy el asistente de Brasaland.</p>
            <p className="text-muted">
              Puedo ayudarte con incidencias, candidatos, operaciones y más.
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <ChatMessageItem key={message.message_id} message={message} />
          ))
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="chat-websocket__input-area">
        {/* Botón abort (solo visible durante generación) */}
        {generationStatus === 'generating' && (
          <div className="chat-websocket__abort-container">
            <button
              className="chat-websocket__abort-btn"
              onClick={handleAbort}
            >
              ⏹ Detener respuesta
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="chat-websocket__form">
          <input
            type="text"
            className="chat-websocket__input"
            placeholder={
              status === 'connected'
                ? 'Escribe tu mensaje...'
                : 'Conectando...'
            }
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            disabled={status !== 'connected'}
          />
          <button
            type="submit"
            className="chat-websocket__send-btn"
            disabled={status !== 'connected' || !inputValue.trim()}
          >
            ➤
          </button>
        </form>
      </div>
    </div>
  );
}

// ============================================================
// MESSAGE ITEM COMPONENT
// ============================================================

interface ChatMessageItemProps {
  message: ChatMessage;
}

function ChatMessageItem({ message }: ChatMessageItemProps) {
  const isUser = message.role === 'user';
  const isInterrupted = message.status === 'interrupted';
  const isStreaming = message.status === 'streaming';

  return (
    <div
      className={`chat-message chat-message--${message.role} ${
        isInterrupted ? 'chat-message--interrupted' : ''
      }`}
    >
      <div className="chat-message__header">
        <span className="chat-message__role">
          {isUser ? '👤 Tú' : '🤖 Asistente'}
        </span>
        {isInterrupted && (
          <span className="chat-message__badge chat-message__badge--interrupted">
            [Interrumpido]
          </span>
        )}
        {isStreaming && (
          <span className="chat-message__badge chat-message__badge--streaming">
            <span className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </span>
          </span>
        )}
      </div>

      <div className="chat-message__content">
        {message.content}
        {isStreaming && <span className="cursor-blink">|</span>}
      </div>

      <div className="chat-message__footer">
        <span className="chat-message__time">
          {formatTime(message.created_at)}
        </span>
      </div>
    </div>
  );
}

// ============================================================
// HELPERS
// ============================================================

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString('es-ES', {
    hour: '2-digit',
    minute: '2-digit',
  });
}
