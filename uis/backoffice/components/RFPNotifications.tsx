/**
 * React Component - RFP Real-Time Notifications
 *
 * Características:
 * - Consume hook useRFPNotifications
 * - Muestra lista de tickets en tiempo real
 * - Badge de "nuevos tickets" sin leer
 * - Indicador de conexión SSE
 * - Notificación browser (Web Notifications API)
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useRFPNotifications, RFPTicket } from '../hooks/useRFPNotifications';

// ============================================================
// TYPES
// ============================================================

interface RFPNotificationsProps {
  jwtToken: string;
  onTicketClick?: (ticket: RFPTicket) => void;
}

// ============================================================
// COMPONENT
// ============================================================

export function RFPNotifications({
  jwtToken,
  onTicketClick,
}: RFPNotificationsProps) {
  // Hook SSE
  const {
    tickets,
    isConnected,
    connectionError,
    reconnectAttempts,
  } = useRFPNotifications(jwtToken, {
    apiBaseUrl: '/api',
    autoConnect: true,
    onTicketCreated: handleTicketCreated,
    onError: handleError,
  });

  // State
  const [unreadCount, setUnreadCount] = useState(0);
  const [lastSeenTicketId, setLastSeenTicketId] = useState<number | null>(null);

  // ============================================================
  // HANDLERS
  // ============================================================

  function handleTicketCreated(ticket: RFPTicket) {
    console.log('[RFPNotifications] Nuevo ticket recibido:', ticket);

    // Incrementar contador de no leídos
    setUnreadCount((prev) => prev + 1);

    // Mostrar notificación del navegador
    showBrowserNotification(ticket);
  }

  function handleError(error: Error) {
    console.error('[RFPNotifications] Error SSE:', error);
    // Aquí podrías mostrar un toast/alert al usuario
  }

  const handleTicketItemClick = useCallback(
    (ticket: RFPTicket) => {
      // Marcar como "visto" al hacer click
      if (lastSeenTicketId === null || ticket.ticket_id > lastSeenTicketId) {
        setLastSeenTicketId(ticket.ticket_id);
      }

      // Callback externo
      if (onTicketClick) {
        onTicketClick(ticket);
      }
    },
    [lastSeenTicketId, onTicketClick]
  );

  const markAllAsRead = useCallback(() => {
    if (tickets.length > 0) {
      setLastSeenTicketId(tickets[0].ticket_id); // El más reciente
      setUnreadCount(0);
    }
  }, [tickets]);

  // ============================================================
  // BROWSER NOTIFICATIONS
  // ============================================================

  useEffect(() => {
    // Solicitar permiso para notificaciones del navegador
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  function showBrowserNotification(ticket: RFPTicket) {
    if ('Notification' in window && Notification.permission === 'granted') {
      const notification = new Notification('Nueva RFP Recibida', {
        body: `Ticket #${ticket.ticket_id}: ${ticket.filename}`,
        icon: '/rfp-icon.png', // Ajustar ruta
        tag: `rfp-${ticket.ticket_id}`, // Evitar duplicados
        requireInteraction: false,
      });

      notification.onclick = () => {
        window.focus();
        handleTicketItemClick(ticket);
        notification.close();
      };
    }
  }

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="rfp-notifications">
      {/* Header con estado de conexión */}
      <div className="rfp-notifications__header">
        <div className="rfp-notifications__title">
          <h2>RFP Tickets</h2>
          {unreadCount > 0 && (
            <span className="badge badge--unread" onClick={markAllAsRead}>
              {unreadCount} nuevos
            </span>
          )}
        </div>

        <div className="rfp-notifications__status">
          {isConnected ? (
            <span className="status status--connected">
              🟢 Tiempo real
            </span>
          ) : (
            <span className="status status--reconnecting">
              🟡 Reconectando{reconnectAttempts > 0 && ` (${reconnectAttempts})`}...
            </span>
          )}
        </div>
      </div>

      {/* Error banner */}
      {connectionError && (
        <div className="rfp-notifications__error">
          <strong>Error de conexión:</strong> {connectionError.message}
        </div>
      )}

      {/* Lista de tickets */}
      <div className="rfp-notifications__list">
        {tickets.length === 0 ? (
          <div className="rfp-notifications__empty">
            <p>No hay tickets de RFP todavía.</p>
            <p className="text-muted">
              Los nuevos tickets aparecerán aquí automáticamente.
            </p>
          </div>
        ) : (
          tickets.map((ticket) => (
            <div
              key={ticket.ticket_id}
              className={`rfp-ticket ${
                lastSeenTicketId === null || ticket.ticket_id > lastSeenTicketId
                  ? 'rfp-ticket--unread'
                  : ''
              }`}
              onClick={() => handleTicketItemClick(ticket)}
            >
              <div className="rfp-ticket__header">
                <h3 className="rfp-ticket__id">
                  Ticket #{ticket.ticket_id}
                  {lastSeenTicketId === null || ticket.ticket_id > lastSeenTicketId ? (
                    <span className="badge badge--new">NUEVO</span>
                  ) : null}
                </h3>
                <span className={`rfp-ticket__status status--${ticket.status}`}>
                  {ticket.status}
                </span>
              </div>

              <div className="rfp-ticket__body">
                <p className="rfp-ticket__filename">
                  📄 {ticket.filename}
                </p>
                {ticket.client_name && (
                  <p className="rfp-ticket__client">
                    🏢 {ticket.client_name}
                  </p>
                )}
                <p className="rfp-ticket__date">
                  🕒 {formatDate(ticket.created_at)}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ============================================================
// HELPERS
// ============================================================

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Ahora mismo';
  if (diffMins < 60) return `Hace ${diffMins} min`;
  if (diffMins < 1440) {
    const hours = Math.floor(diffMins / 60);
    return `Hace ${hours} hora${hours > 1 ? 's' : ''}`;
  }

  // Formato completo
  return date.toLocaleString('es-ES', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
