# Ejemplo de Integración SSE en RFPTable

**Archivo**: `uis/backoffice/components/RFPTable.tsx`

Este documento muestra cómo integrar el sistema de notificaciones SSE en la tabla principal de tickets RFP.

---

## 📋 Integración Básica

### Opción 1: Component Standalone (Recomendado)

Usar el componente `RFPNotifications` como panel lateral o modal.

```tsx
// uis/backoffice/app/rfp/page.tsx

import { useState } from 'react';
import { RFPNotifications } from '@/components/RFPNotifications';
import { RFPTable } from '@/components/RFPTable';
import '@/components/RFPNotifications.css';

export default function RFPPage() {
  const [selectedTicketId, setSelectedTicketId] = useState<number | null>(null);
  const jwtToken = getJWTToken(); // Obtener desde auth context

  return (
    <div className="rfp-page">
      {/* Panel lateral con notificaciones en tiempo real */}
      <aside className="sidebar">
        <RFPNotifications
          jwtToken={jwtToken}
          onTicketClick={(ticket) => {
            setSelectedTicketId(ticket.ticket_id);
            // Scroll a la fila en la tabla
            // O abrir modal de detalles
          }}
        />
      </aside>

      {/* Tabla principal */}
      <main className="main-content">
        <RFPTable selectedTicketId={selectedTicketId} />
      </main>
    </div>
  );
}
```

**CSS del Layout**:
```css
.rfp-page {
  display: grid;
  grid-template-columns: 400px 1fr;
  height: 100vh;
  gap: 1rem;
}

.sidebar {
  border-right: 1px solid var(--border-color);
  overflow: hidden;
}

.main-content {
  padding: 1rem;
  overflow-y: auto;
}

@media (max-width: 1024px) {
  .rfp-page {
    grid-template-columns: 1fr;
    grid-template-rows: 300px 1fr;
  }

  .sidebar {
    border-right: none;
    border-bottom: 1px solid var(--border-color);
  }
}
```

---

### Opción 2: Hook Directo en RFPTable

Usar solo el hook para actualizar la tabla en tiempo real.

```tsx
// uis/backoffice/components/RFPTable.tsx

import { useRFPNotifications } from '@/hooks/useRFPNotifications';
import { useEffect, useState } from 'react';

interface RFPTableProps {
  jwtToken: string;
}

export function RFPTable({ jwtToken }: RFPTableProps) {
  const [localTickets, setLocalTickets] = useState<RFPTicket[]>([]);

  // Conectar a SSE
  const {
    tickets: realtimeTickets,
    isConnected,
    reconnectAttempts,
  } = useRFPNotifications(jwtToken, {
    apiBaseUrl: '/api',
    autoConnect: true,
    onTicketCreated: (ticket) => {
      console.log('🔔 Nuevo ticket recibido:', ticket);
      
      // Mostrar toast notification
      showToast(`Nuevo ticket #${ticket.ticket_id} recibido`);
    },
  });

  // Sincronizar tickets en tiempo real con estado local
  useEffect(() => {
    setLocalTickets(realtimeTickets);
  }, [realtimeTickets]);

  return (
    <div className="rfp-table">
      {/* Indicador de conexión */}
      <div className="table-header">
        <h2>RFP Tickets</h2>
        <div className={`connection-indicator ${isConnected ? 'connected' : 'reconnecting'}`}>
          {isConnected ? (
            <span>🟢 Tiempo real</span>
          ) : (
            <span>🟡 Reconectando... ({reconnectAttempts})</span>
          )}
        </div>
      </div>

      {/* Tabla */}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Archivo</th>
            <th>Estado</th>
            <th>Cliente</th>
            <th>Fecha</th>
          </tr>
        </thead>
        <tbody>
          {localTickets.map((ticket) => (
            <tr key={ticket.ticket_id} className="ticket-row">
              <td>#{ticket.ticket_id}</td>
              <td>{ticket.filename}</td>
              <td>
                <span className={`badge status--${ticket.status}`}>
                  {ticket.status}
                </span>
              </td>
              <td>{ticket.client_name || '—'}</td>
              <td>{formatDate(ticket.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleString('es-ES', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function showToast(message: string) {
  // Implementar con librería de toast (react-hot-toast, sonner, etc.)
  console.log('[Toast]', message);
}
```

---

### Opción 3: Hybrid (Notificaciones + Tabla Actualizada)

Combinar ambas: panel de notificaciones + tabla que se actualiza automáticamente.

```tsx
// uis/backoffice/app/rfp/page.tsx

import { RFPNotifications } from '@/components/RFPNotifications';
import { RFPTable } from '@/components/RFPTable';
import { useRFPNotifications } from '@/hooks/useRFPNotifications';
import '@/components/RFPNotifications.css';

export default function RFPPage() {
  const jwtToken = getJWTToken();

  // Hook compartido para notificaciones y tabla
  const {
    tickets,
    isConnected,
    reconnectAttempts,
  } = useRFPNotifications(jwtToken, {
    autoConnect: true,
    onTicketCreated: (ticket) => {
      // Notificación browser
      new Notification('Nueva RFP', {
        body: `Ticket #${ticket.ticket_id}: ${ticket.filename}`,
      });
    },
  });

  return (
    <div className="rfp-page-hybrid">
      {/* Sidebar: Solo últimos 10 tickets */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h3>Últimos Tickets</h3>
          {isConnected ? (
            <span className="status-dot connected"></span>
          ) : (
            <span className="status-dot reconnecting"></span>
          )}
        </div>

        {/* Lista simplificada */}
        <div className="ticket-list">
          {tickets.slice(0, 10).map((ticket) => (
            <div key={ticket.ticket_id} className="ticket-item">
              <span className="ticket-id">#{ticket.ticket_id}</span>
              <span className="ticket-filename">{ticket.filename}</span>
              <span className={`ticket-status ${ticket.status}`}>
                {ticket.status}
              </span>
            </div>
          ))}
        </div>
      </aside>

      {/* Main: Tabla completa con paginación */}
      <main className="main-content">
        <RFPTable
          tickets={tickets}
          isRealtime={isConnected}
        />
      </main>
    </div>
  );
}
```

---

## 🔐 Autenticación JWT

Obtener el token desde el contexto de autenticación:

```tsx
// uis/backoffice/contexts/AuthContext.tsx

import { createContext, useContext, useState, useEffect } from 'react';

interface AuthContextType {
  jwtToken: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [jwtToken, setJwtToken] = useState<string | null>(null);

  useEffect(() => {
    // Cargar token desde localStorage
    const token = localStorage.getItem('jwt_token');
    if (token) {
      setJwtToken(token);
    }
  }, []);

  const login = async (username: string, password: string) => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json();
    setJwtToken(data.access_token);
    localStorage.setItem('jwt_token', data.access_token);
  };

  const logout = () => {
    setJwtToken(null);
    localStorage.removeItem('jwt_token');
  };

  return (
    <AuthContext.Provider
      value={{
        jwtToken,
        isAuthenticated: !!jwtToken,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
```

**Uso en RFPPage**:
```tsx
import { useAuth } from '@/contexts/AuthContext';

export default function RFPPage() {
  const { jwtToken, isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  return (
    <RFPNotifications jwtToken={jwtToken!} />
  );
}
```

---

## 🎨 Toast Notifications (Opcional)

Usar librería como `react-hot-toast` para notificaciones visuales:

```bash
npm install react-hot-toast
```

```tsx
// uis/backoffice/app/layout.tsx

import { Toaster } from 'react-hot-toast';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
          }}
        />
      </body>
    </html>
  );
}
```

```tsx
// En useRFPNotifications callback

import toast from 'react-hot-toast';

useRFPNotifications(jwtToken, {
  onTicketCreated: (ticket) => {
    toast.success(
      `Nuevo ticket #${ticket.ticket_id}: ${ticket.filename}`,
      {
        icon: '📄',
        duration: 5000,
      }
    );
  },
  onError: (error) => {
    toast.error(`Error de conexión: ${error.message}`);
  },
});
```

---

## 🧪 Testing en Desarrollo

### 1. Backend Mock (sin DB real)

Crear endpoint de test para simular eventos:

```python
# services/routers/notifications.py

@router.post("/test/publish")
async def test_publish_event(ticket_id: int = 123):
    """
    SOLO DESARROLLO: Publica evento de prueba.
    """
    event = RFPTicketEvent(
        event_type="rfp_ticket_created",
        ticket_id=ticket_id,
        status="analizando",
        filename=f"test_rfp_{ticket_id}.pdf",
        client_name="Test Corp",
        created_at=datetime.utcnow().isoformat()
    )
    
    await connection_manager.publish(event)
    
    return {"message": f"Test event published for ticket {ticket_id}"}
```

**Uso con curl**:
```bash
# Terminal 1: Conectar SSE
curl -N -H "Authorization: Bearer test_token_1234567890" \
  http://localhost:8000/api/notifications/sse

# Terminal 2: Publicar evento de prueba
curl -X POST http://localhost:8000/api/notifications/test/publish?ticket_id=999
```

### 2. Frontend Mock (sin backend)

Simular eventos en el hook:

```tsx
// uis/backoffice/hooks/useRFPNotifications.ts

// Agregar modo mock para desarrollo
const MOCK_MODE = process.env.NEXT_PUBLIC_SSE_MOCK === 'true';

if (MOCK_MODE) {
  // Simular eventos cada 5 segundos
  useEffect(() => {
    const interval = setInterval(() => {
      const mockTicket: RFPTicket = {
        ticket_id: Math.floor(Math.random() * 1000),
        status: 'analizando',
        filename: `mock_rfp_${Date.now()}.pdf`,
        client_name: 'Mock Corp',
        created_at: new Date().toISOString(),
      };

      setTickets((prev) => [mockTicket, ...prev]);

      if (onTicketCreated) {
        onTicketCreated(mockTicket);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, []);
}
```

**Activar mock**:
```bash
# .env.local
NEXT_PUBLIC_SSE_MOCK=true
```

---

## 📊 Métricas y Monitoring

Agregar logging para monitorear el sistema:

```tsx
// useRFPNotifications.ts

useEffect(() => {
  console.log('[SSE Metrics]', {
    isConnected,
    ticketsCount: tickets.length,
    reconnectAttempts,
    lastEventAt: tickets[0]?.created_at || 'N/A',
  });
}, [isConnected, tickets.length, reconnectAttempts]);
```

Backend:
```python
# services/notifications/manager.py

def get_stats(self) -> Dict[str, Any]:
    """Estadísticas del connection manager."""
    return {
        "active_connections": len(self.connections),
        "total_events_sent": self._total_events_sent,
        "uptime_seconds": time.time() - self._start_time,
    }
```

---

## ✅ Checklist de Integración

- [ ] Instalar dependencias (`react-hot-toast`, etc.)
- [ ] Crear `AuthContext` con JWT
- [ ] Importar hook `useRFPNotifications`
- [ ] Importar componente `RFPNotifications`
- [ ] Importar CSS `RFPNotifications.css`
- [ ] Conectar hook con token JWT
- [ ] Agregar indicador de conexión
- [ ] Implementar toast notifications
- [ ] Probar reconexión (apagar/prender backend)
- [ ] Verificar deduplicación (mismo ticket no aparece 2 veces)
- [ ] Testing end-to-end

---

**Notas Finales**:
- El hook maneja automáticamente la reconexión con backoff exponencial
- Los eventos se deduplicán por `ticket_id` en memoria
- El heartbeat keep-alive previene timeouts de proxies/gateways
- El componente soporta light/dark mode automáticamente

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
