/**
 * React Component - Brasaland Incident Notifications
 *
 * DOMINIO: Sistema de Análisis de Incidencias Postventa
 * Usuario: Operaciones (Felipe Guerrero) + Dirección (Mariana Restrepo)
 * Locales: 14 restaurantes (10 CO + 4 US)
 *
 * Características:
 * - Lista de incidencias en tiempo real
 * - Badge de severidad (baja, media, alta, critica)
 * - Indicador de conexión SSE
 * - Notificaciones browser
 * - Filtro por país y local
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useIncidentNotifications, BrasalandIncident } from '../hooks/useIncidentNotifications';

// ============================================================
// TYPES
// ============================================================

interface IncidentNotificationsProps {
  jwtToken: string;
  onIncidentClick?: (incident: BrasalandIncident) => void;
}

// ============================================================
// COMPONENT
// ============================================================

export function IncidentNotifications({
  jwtToken,
  onIncidentClick,
}: IncidentNotificationsProps) {
  // Hook SSE
  const {
    incidents,
    isConnected,
    connectionError,
    reconnectAttempts,
  } = useIncidentNotifications(jwtToken, {
    apiBaseUrl: '/api',
    autoConnect: true,
    onIncidentCreated: handleIncidentCreated,
    onError: handleError,
  });

  // State
  const [unreadCount, setUnreadCount] = useState(0);
  const [lastSeenIncidentId, setLastSeenIncidentId] = useState<number | null>(null);
  const [filterCountry, setFilterCountry] = useState<string | null>(null);

  // ============================================================
  // HANDLERS
  // ============================================================

  function handleIncidentCreated(incident: BrasalandIncident) {
    console.log('[IncidentNotifications] Nueva incidencia recibida:', incident);

    // Incrementar no leídos
    setUnreadCount((prev) => prev + 1);

    // Notificación browser
    showBrowserNotification(incident);
  }

  function handleError(error: Error) {
    console.error('[IncidentNotifications] Error SSE:', error);
  }

  const handleIncidentItemClick = useCallback(
    (incident: BrasalandIncident) => {
      // Marcar como visto
      if (lastSeenIncidentId === null || incident.incident_id > lastSeenIncidentId) {
        setLastSeenIncidentId(incident.incident_id);
      }

      // Callback externo
      if (onIncidentClick) {
        onIncidentClick(incident);
      }
    },
    [lastSeenIncidentId, onIncidentClick]
  );

  const markAllAsRead = useCallback(() => {
    if (incidents.length > 0) {
      setLastSeenIncidentId(incidents[0].incident_id);
      setUnreadCount(0);
    }
  }, [incidents]);

  // ============================================================
  // BROWSER NOTIFICATIONS
  // ============================================================

  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  function showBrowserNotification(incident: BrasalandIncident) {
    if ('Notification' in window && Notification.permission === 'granted') {
      const severityEmoji = {
        'baja': '🟢',
        'media': '🟡',
        'alta': '🟠',
        'critica': '🔴',
      }[incident.severity] || '📋';

      const notification = new Notification('Nueva Incidencia - Brasaland', {
        body: `${severityEmoji} ${incident.local_name} (${incident.country})\n${incident.category}: ${incident.description}`,
        icon: '/brasaland-logo.png',
        tag: `incident-${incident.incident_id}`,
        requireInteraction: incident.severity === 'critica',
      });

      notification.onclick = () => {
        window.focus();
        handleIncidentItemClick(incident);
        notification.close();
      };
    }
  }

  // ============================================================
  // FILTRADO
  // ============================================================

  const filteredIncidents = filterCountry
    ? incidents.filter(i => i.country === filterCountry)
    : incidents;

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="incident-notifications">
      {/* Header */}
      <div className="incident-notifications__header">
        <div className="incident-notifications__title">
          <h2>Incidencias Postventa</h2>
          {unreadCount > 0 && (
            <span className="badge badge--unread" onClick={markAllAsRead}>
              {unreadCount} nuevas
            </span>
          )}
        </div>

        <div className="incident-notifications__status">
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

      {/* Filtros */}
      <div className="incident-notifications__filters">
        <button
          className={filterCountry === null ? 'filter-btn active' : 'filter-btn'}
          onClick={() => setFilterCountry(null)}
        >
          Todos ({incidents.length})
        </button>
        <button
          className={filterCountry === 'CO' ? 'filter-btn active' : 'filter-btn'}
          onClick={() => setFilterCountry('CO')}
        >
          🇨🇴 Colombia ({incidents.filter(i => i.country === 'CO').length})
        </button>
        <button
          className={filterCountry === 'US' ? 'filter-btn active' : 'filter-btn'}
          onClick={() => setFilterCountry('US')}
        >
          🇺🇸 USA ({incidents.filter(i => i.country === 'US').length})
        </button>
      </div>

      {/* Error */}
      {connectionError && (
        <div className="incident-notifications__error">
          <strong>Error de conexión:</strong> {connectionError.message}
        </div>
      )}

      {/* Lista */}
      <div className="incident-notifications__list">
        {filteredIncidents.length === 0 ? (
          <div className="incident-notifications__empty">
            <p>No hay incidencias todavía.</p>
            <p className="text-muted">
              Las nuevas incidencias aparecerán aquí automáticamente.
            </p>
          </div>
        ) : (
          filteredIncidents.map((incident) => (
            <div
              key={incident.incident_id}
              className={`incident-item ${
                lastSeenIncidentId === null || incident.incident_id > lastSeenIncidentId
                  ? 'incident-item--unread'
                  : ''
              } incident-item--${incident.severity}`}
              onClick={() => handleIncidentItemClick(incident)}
            >
              <div className="incident-item__header">
                <h3 className="incident-item__id">
                  Incidencia #{incident.incident_id}
                  {lastSeenIncidentId === null || incident.incident_id > lastSeenIncidentId ? (
                    <span className="badge badge--new">NUEVA</span>
                  ) : null}
                </h3>
                <span className={`incident-item__severity severity--${incident.severity}`}>
                  {incident.severity.toUpperCase()}
                </span>
              </div>

              <div className="incident-item__body">
                <p className="incident-item__local">
                  📍 {incident.local_name} ({incident.country === 'CO' ? '🇨🇴' : '🇺🇸'})
                </p>
                <p className="incident-item__category">
                  🏷️ {formatCategory(incident.category)}
                </p>
                <p className="incident-item__description">
                  {incident.description}
                </p>
                {incident.customer_name && (
                  <p className="incident-item__customer">
                    👤 Cliente: {incident.customer_name}
                  </p>
                )}
                <p className="incident-item__date">
                  🕒 {formatDate(incident.created_at)}
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

function formatCategory(category: string): string {
  const labels: Record<string, string> = {
    'calidad_comida': 'Calidad de Comida',
    'servicio': 'Servicio al Cliente',
    'tiempo_espera': 'Tiempo de Espera',
    'higiene': 'Higiene y Limpieza',
    'ambiente': 'Ambiente del Local',
  };
  return labels[category] || category;
}

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

  return date.toLocaleString('es-ES', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
