# 🚀 Guía de Integración WebSocket Chat - Paso a Paso

**Sistema**: Chat Bidireccional con Token Streaming  
**Dominio**: Brasaland Digital  
**Audiencia**: Desarrolladores implementando el sistema

---

## 📋 Índice

1. [Requisitos Previos](#requisitos-previos)
2. [Backend: Integración con LangGraph](#backend-integración-con-langgraph)
3. [Backend: Base de Datos PostgreSQL](#backend-base-de-datos-postgresql)
4. [Backend: Autenticación JWT Real](#backend-autenticación-jwt-real)
5. [Frontend: Integración en Dashboard](#frontend-integración-en-dashboard)
6. [Testing End-to-End](#testing-end-to-end)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)

---

## 1. Requisitos Previos

### Dependencias Python

```bash
# Backend
pip install fastapi
pip install uvicorn[standard]
pip install websockets
pip install python-jose[cryptography]  # JWT
pip install passlib[bcrypt]            # Passwords
pip install sqlalchemy
pip install asyncpg                    # PostgreSQL async
pip install langgraph                  # Agente IA
pip install langchain-anthropic        # Claude
```

### Dependencias Frontend

```bash
# Frontend (ya instaladas en monorepo Brasaland)
cd uis/backoffice
# React, TypeScript, Next.js ya configurados
```

### Variables de Entorno

```bash
# .env

# JWT
SECRET_KEY=your-secret-key-here-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/brasaland

# Anthropic API (para LangGraph)
ANTHROPIC_API_KEY=sk-ant-...

# WebSocket
WS_HOST=0.0.0.0
WS_PORT=8000
```

---

## 2. Backend: Integración con LangGraph

### Paso 2.1: Crear el Agente

```python
# services/agent/graph.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage
from typing import TypedDict, Annotated, Sequence
import operator

# ============================================================
# STATE
# ============================================================

class AgentState(TypedDict):
    """Estado del agente de soporte Brasaland."""
    messages: Annotated[Sequence[HumanMessage | AIMessage], operator.add]
    session_id: str
    user_id: str


# ============================================================
# NODES
# ============================================================

async def agent_node(state: AgentState):
    """Nodo del agente: Invoca Claude con streaming."""
    model = ChatAnthropic(
        model="claude-sonnet-4-5",
        temperature=0.7,
        streaming=True  # ← CRÍTICO para token streaming
    )
    
    # Prompt de sistema
    system_prompt = """
    Eres el asistente IA de Brasaland Digital, una cadena de 14 restaurantes
    de cocina a la brasa (10 en Colombia + 4 en Florida, USA).
    
    Puedes ayudar con:
    - Incidencias postventa (calidad, servicio, tiempos)
    - Candidaturas ATS (Cocinero, Mesero, Cajero, Supervisor, Gerente)
    - Operaciones (ventas, inventarios, alertas)
    - Consultas sobre los 14 locales
    
    Sé conciso, profesional y cálido.
    """
    
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    
    response = await model.ainvoke(messages)
    
    return {"messages": [response]}


# ============================================================
# GRAPH
# ============================================================

def build_agent_graph(checkpointer) -> StateGraph:
    """Construye grafo del agente."""
    workflow = StateGraph(AgentState)
    
    # Nodos
    workflow.add_node("agent", agent_node)
    
    # Edges
    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)
    
    # Compilar con checkpointer
    graph = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=[]  # Sin HITL (usamos abort stream, no interrupt)
    )
    
    return graph


# ============================================================
# FACTORY
# ============================================================

_graph_instance = None

def get_agent_graph():
    """Singleton del grafo del agente."""
    global _graph_instance
    
    if _graph_instance is None:
        # Checkpointer PostgreSQL
        from services.database import get_database_url
        
        checkpointer = PostgresSaver.from_conn_string(
            get_database_url()
        )
        
        _graph_instance = build_agent_graph(checkpointer)
    
    return _graph_instance
```

### Paso 2.2: Actualizar `stream_agent_response()`

```python
# services/routers/chat_ws.py

async def stream_agent_response(
    session_id: str,
    user_input: str,
    message_id: str
):
    """
    PRODUCCIÓN: Streaming con LangGraph astream_events.
    
    REEMPLAZA: Mock actual
    """
    from services.agent.graph import get_agent_graph
    from langchain_core.messages import HumanMessage
    
    graph = get_agent_graph()
    config = {
        "configurable": {
            "thread_id": session_id  # ← session_id = thread_id
        }
    }
    
    accumulated_content = ""
    
    try:
        # Stream desde LangGraph
        async for event in graph.astream_events(
            {
                "messages": [HumanMessage(content=user_input)],
                "session_id": session_id
            },
            config=config,
            version="v2"
        ):
            # Filtrar eventos de streaming de tokens
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                
                # Extraer delta (puede ser str o AIMessageChunk)
                if hasattr(chunk, 'content'):
                    delta = chunk.content
                elif isinstance(chunk, str):
                    delta = chunk
                else:
                    continue
                
                if not delta:
                    continue
                
                accumulated_content += delta
                
                # Broadcast token chunk
                await session_manager.broadcast_to_session(
                    session_id,
                    {
                        "type": "token_chunk",
                        "delta": delta,
                        "message_id": message_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        
        # Generación completada
        await session_manager.broadcast_to_session(
            session_id,
            {
                "type": "generation_completed",
                "message_id": message_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        # Guardar mensaje completo
        await save_message(
            session_id=session_id,
            message_id=message_id,
            role="assistant",
            content=accumulated_content.strip(),
            status="completed"
        )
    
    except asyncio.CancelledError:
        # ABORT: Guardar parcial como interrupted
        logger.info(
            f"[WS] Generación abortada, guardando parcial: "
            f"{accumulated_content[:50]}..."
        )
        
        await save_message(
            session_id=session_id,
            message_id=message_id,
            role="assistant",
            content=accumulated_content.strip(),
            status="interrupted"
        )
        
        raise  # Re-raise para limpiar en caller
```

---

## 3. Backend: Base de Datos PostgreSQL

### Paso 3.1: Modelo SQLAlchemy

```python
# services/models/chat.py

from sqlalchemy import Column, Integer, String, DateTime, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class MessageStatus(enum.Enum):
    """Estados del mensaje."""
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    STREAMING = "streaming"


class ChatMessage(Base):
    """Modelo de mensaje de chat."""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(50), unique=True, nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    status = Column(
        Enum(MessageStatus),
        nullable=False,
        default=MessageStatus.COMPLETED
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatSession(Base):
    """Modelo de sesión de chat."""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_activity = Column(DateTime, nullable=False, default=datetime.utcnow)
```

### Paso 3.2: Conexión Async

```python
# services/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # True para debug
    pool_size=20,
    max_overflow=40
)

AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db():
    """Dependency para obtener sesión de BD."""
    async with AsyncSessionLocal() as session:
        yield session


def get_database_url():
    """Retorna URL de BD para checkpointer."""
    return DATABASE_URL
```

### Paso 3.3: Implementar Funciones de Persistencia

```python
# services/routers/chat_ws.py

from services.database import AsyncSessionLocal
from services.models.chat import ChatMessage, MessageStatus
from sqlalchemy import select

async def load_chat_history(session_id: str) -> list:
    """
    Carga historial de chat desde BD.
    
    Returns:
        Lista de mensajes ordenados por created_at
    """
    async with AsyncSessionLocal() as db:
        stmt = select(ChatMessage).where(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at)
        
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        return [
            {
                "message_id": msg.message_id,
                "role": msg.role,
                "content": msg.content,
                "status": msg.status.value,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]


async def save_message(
    session_id: str,
    message_id: str,
    role: str,
    content: str,
    status: str
):
    """Guarda mensaje en BD."""
    async with AsyncSessionLocal() as db:
        message = ChatMessage(
            message_id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            status=MessageStatus(status)
        )
        
        db.add(message)
        await db.commit()
        
        logger.info(
            f"[DB] Guardado mensaje {message_id} ({role}, {status})"
        )


async def save_partial_message(
    session_id: str,
    message_id: str,
    status: str
):
    """Actualiza status de mensaje a interrupted."""
    async with AsyncSessionLocal() as db:
        stmt = select(ChatMessage).where(
            ChatMessage.message_id == message_id
        )
        result = await db.execute(stmt)
        message = result.scalar_one_or_none()
        
        if message:
            message.status = MessageStatus(status)
            await db.commit()
            
            logger.info(f"[DB] Actualizado mensaje {message_id} a {status}")
```

### Paso 3.4: Migraciones Alembic

```bash
# Inicializar Alembic
alembic init alembic

# Configurar alembic.ini
# sqlalchemy.url = postgresql+asyncpg://user:password@localhost:5432/brasaland

# Crear migración
alembic revision --autogenerate -m "create chat tables"

# Aplicar migración
alembic upgrade head
```

---

## 4. Backend: Autenticación JWT Real

### Paso 4.1: Configuración

```python
# services/auth/jwt.py

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException
import os

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: timedelta = None):
    """Crea token JWT."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verifica y decodifica token JWT.
    
    Returns:
        Payload del token
    
    Raises:
        HTTPException 401 si token inválido
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(401, "Invalid token payload")
        
        return payload
    
    except JWTError as e:
        raise HTTPException(401, f"Invalid token: {str(e)}")
```

### Paso 4.2: Actualizar `verify_jwt_from_query()`

```python
# services/routers/chat_ws.py

from services.auth.jwt import verify_token

async def verify_jwt_from_query(token: Optional[str]) -> str:
    """
    Verifica token JWT desde query string.
    
    PRODUCCIÓN: Usa python-jose
    """
    if not token:
        raise HTTPException(401, "Missing token in query string")
    
    # Verificar con jose
    payload = verify_token(token)
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(401, "Invalid token payload")
    
    return user_id
```

---

## 5. Frontend: Integración en Dashboard

### Paso 5.1: Crear Página de Chat

```tsx
// uis/backoffice/app/chat/page.tsx

'use client';

import { ChatWebSocket } from '@/components/ChatWebSocket';
import '@/components/ChatWebSocket.css';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';

export default function ChatPage() {
  const router = useRouter();
  const { jwtToken, user, isAuthenticated } = useAuth();
  const [sessionId, setSessionId] = useState<string>('');

  useEffect(() => {
    // Generar session_id único por usuario
    if (user?.id) {
      setSessionId(`session_${user.id}_${Date.now()}`);
    }
  }, [user]);

  if (!isAuthenticated) {
    router.push('/login');
    return null;
  }

  if (!sessionId) {
    return <div>Cargando...</div>;
  }

  return (
    <div className="chat-page-container">
      <ChatWebSocket
        sessionId={sessionId}
        jwtToken={jwtToken!}
        onClose={() => router.push('/dashboard')}
      />
    </div>
  );
}
```

### Paso 5.2: Agregar en Navegación

```tsx
// uis/backoffice/components/Sidebar.tsx

<nav>
  <Link href="/dashboard">Dashboard</Link>
  <Link href="/incidents">Incidencias</Link>
  <Link href="/candidates">Candidatos</Link>
  <Link href="/chat">💬 Asistente IA</Link>  {/* ← NUEVO */}
  <Link href="/settings">Configuración</Link>
</nav>
```

### Paso 5.3: Configurar Proxy WebSocket (Next.js)

```javascript
// uis/backoffice/next.config.js

module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
      // WebSocket proxy
      {
        source: '/ws/:path*',
        destination: 'http://localhost:8000/ws/:path*',
      },
    ];
  },
};
```

---

## 6. Testing End-to-End

### Paso 6.1: Ejecutar Tests Automatizados

```bash
# Backend tests
cd /path/to/project
pytest tests/test_chat_ws.py -v

# Salida esperada:
# test_websocket_requires_jwt_token PASSED
# test_websocket_accepts_valid_token PASSED
# test_websocket_token_streaming_contract PASSED
# test_websocket_abort_cancels_generation PASSED
# test_websocket_reconnect_rehydrates_history PASSED
# ... (15 tests total)
```

### Paso 6.2: Test Manual con wscat

```bash
# Instalar wscat
npm install -g wscat

# Conectar
wscat -c "ws://localhost:8000/ws/chat/test_session?token=YOUR_JWT_TOKEN"

# Enviar mensaje
> {"type": "user_message", "content": "Hola, ¿cuántos locales tiene Brasaland?", "message_id": "msg_test_1"}

# Esperar respuesta (token chunks)
< {"type":"token_chunk","delta":"Brasaland","message_id":"msg_xxx",...}
< {"type":"token_chunk","delta":" tiene","message_id":"msg_xxx",...}
...
< {"type":"generation_completed","message_id":"msg_xxx",...}

# Enviar abort
> {"type": "abort"}

# Debe recibir interrupted
< {"type":"generation_interrupted","message_id":"msg_xxx","reason":"user_abort"}
```

### Paso 6.3: Test con UI Real

1. **Iniciar backend**:
```bash
cd services
uvicorn main:app --reload --port 8000
```

2. **Iniciar frontend**:
```bash
cd uis/backoffice
npm run dev
```

3. **Navegador**:
- Ir a `http://localhost:3000/chat`
- Login con usuario válido
- Enviar mensaje: "Hola, ¿cómo puedo ayudar con Brasaland?"
- Verificar typing effect progresivo
- Enviar nuevo mensaje durante generación
- Verificar badge `[Interrumpido]` en mensaje parcial
- Recargar página (F5)
- Verificar que historial se recupera

---

## 7. Deployment

### Paso 7.1: Docker Compose

```yaml
# docker-compose.yml

version: '3.8'

services:
  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: brasaland
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: brasaland
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # Backend FastAPI
  backend:
    build: ./services
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://brasaland:${DB_PASSWORD}@postgres:5432/brasaland
      SECRET_KEY: ${SECRET_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    depends_on:
      - postgres
    command: uvicorn main:app --host 0.0.0.0 --port 8000

  # Frontend Next.js
  frontend:
    build: ./uis/backoffice
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
    depends_on:
      - backend

volumes:
  postgres_data:
```

### Paso 7.2: Dockerfile Backend

```dockerfile
# services/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY . .

# Exponer puerto WebSocket
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Paso 7.3: Deploy a Producción

```bash
# Build
docker-compose build

# Ejecutar
docker-compose up -d

# Verificar
docker-compose logs -f backend
docker-compose logs -f frontend

# Migrar BD
docker-compose exec backend alembic upgrade head
```

---

## 8. Troubleshooting

### Problema: WebSocket no conecta

**Síntomas**: `ws.onerror` se dispara inmediatamente

**Soluciones**:
1. Verificar que backend esté corriendo: `curl http://localhost:8000/ws/health`
2. Verificar token JWT válido (no expirado)
3. Revisar logs backend: `docker-compose logs backend | grep WS`
4. Verificar CORS si backend está en dominio diferente

### Problema: Tokens no llegan (stuck en "Generando...")

**Síntomas**: `generationStatus` se queda en `'generating'`

**Soluciones**:
1. Verificar integración LangGraph: revisar logs de `stream_agent_response()`
2. Verificar ANTHROPIC_API_KEY configurado
3. Check que `streaming=True` en `ChatAnthropic`
4. Revisar filtro de eventos: `event["event"] == "on_chat_model_stream"`

### Problema: Abort no funciona

**Síntomas**: Tokens siguen llegando después de abort

**Soluciones**:
1. Verificar que `task.cancel()` se está llamando
2. Check que el `except asyncio.CancelledError` está manejado
3. Revisar que la Task está registrada en `active_generations`
4. Logs: `[WS] Generación abortada para sesión...` debe aparecer

### Problema: Mensajes interrumpidos se borran

**Síntomas**: Mensaje parcial desaparece de UI

**Soluciones**:
1. Verificar que `save_partial_message()` se llama con `status="interrupted"`
2. Check que frontend NO limpia mensajes con `status: 'interrupted'`
3. Verificar que `handleGenerationInterrupted()` actualiza el mensaje, no lo elimina

### Problema: Reconexión pierde historial

**Síntomas**: Después de reconectar, mensajes anteriores no aparecen

**Soluciones**:
1. Verificar que `load_chat_history()` se llama al conectar
2. Check que session_id es el mismo antes y después de desconectar
3. Revisar que frame `{type: "history"}` se envía al cliente
4. Logs BD: verificar que mensajes existen en tabla `chat_messages`

---

## ✅ Checklist Final de Integración

- [ ] LangGraph configurado con streaming
- [ ] PostgreSQL conectado
- [ ] Migraciones aplicadas (`chat_messages`, `chat_sessions`)
- [ ] JWT real implementado (python-jose)
- [ ] Frontend integrado en `/chat`
- [ ] Proxy WebSocket configurado (Next.js o nginx)
- [ ] Tests E2E pasando (15/15)
- [ ] Docker Compose funcional
- [ ] Variables de entorno configuradas
- [ ] Logs estructurados
- [ ] Monitoreo (opcional: Prometheus + Grafana)

---

**Soporte**: Consultar `WEBSOCKET_CHAT_IMPLEMENTATION.md` para detalles técnicos  
**Diagramas**: Ver `WEBSOCKET_ARCHITECTURE_DIAGRAM.md`

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
