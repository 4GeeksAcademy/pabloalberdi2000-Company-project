# 🏗️ Arquitectura WebSocket Chat - Diagramas Visuales

**Sistema**: Chat Bidireccional con Token Streaming  
**Dominio**: Brasaland Digital

---

## 🔄 Diagrama 1: Flow Completo de Comunicación

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLIENTE (React)                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────┐                                                     │
│  │ ChatWebSocket.tsx  │                                                     │
│  │                    │                                                     │
│  │  [Input] ─────────────> sendMessage("Hola")                             │
│  │                    │                                                     │
│  │  [Botón Detener] ──────> abortGeneration()                              │
│  │                    │                                                     │
│  │  [Messages List]   │ (renderiza mensajes con typing effect)             │
│  │   - Usuario        │                                                     │
│  │   - Asistente...│  │ (cursor parpadeante)                               │
│  │   - [Interrumpido] │                                                     │
│  └────────┬───────────┘                                                     │
│           │                                                                  │
│           ↓                                                                  │
│  ┌────────────────────┐                                                     │
│  │useChatWebSocket.ts │                                                     │
│  │                    │                                                     │
│  │ messages: []       │ (estado React)                                      │
│  │ status: connected  │                                                     │
│  │ generationStatus   │                                                     │
│  └────────┬───────────┘                                                     │
│           │                                                                  │
│           ↓                                                                  │
│  ┌────────────────────┐                                                     │
│  │  WebSocket API     │                                                     │
│  │  ws://host/ws/chat │                                                     │
│  │  /session_123?     │                                                     │
│  │  token=JWT         │                                                     │
│  └────────┬───────────┘                                                     │
└───────────┼─────────────────────────────────────────────────────────────────┘
            │
            │ TCP Socket (Full-Duplex)
            │
┌───────────▼─────────────────────────────────────────────────────────────────┐
│                          SERVIDOR (FastAPI)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────┐                                                     │
│  │ chat_ws.py         │                                                     │
│  │ @websocket         │                                                     │
│  │ /chat/{session_id} │                                                     │
│  └────────┬───────────┘                                                     │
│           │                                                                  │
│           ↓                                                                  │
│  ┌────────────────────────────────────────────────────────────────┐        │
│  │              ChatSessionManager (Singleton)                     │        │
│  │                                                                  │        │
│  │  sessions: {                                                     │        │
│  │    "session_123": Set(                                           │        │
│  │      "conn_abc",  ← Usuario                                      │        │
│  │      "conn_def",  ← Supervisor (observando)                      │
│  │      "conn_ghi"   ← Dashboard                                    │        │
│  │    )                                                             │        │
│  │  }                                                               │        │
│  │                                                                  │        │
│  │  active_generations: {                                           │        │
│  │    "session_123": asyncio.Task<stream_agent_response>            │        │
│  │  }                                                               │        │
│  │                                                                  │        │
│  │  queues: {                                                       │        │
│  │    "conn_abc": asyncio.Queue ← [event1, event2, ...]           │        │
│  │    "conn_def": asyncio.Queue ← [event1, event2, ...]           │        │
│  │    "conn_ghi": asyncio.Queue ← [event1, event2, ...]           │        │
│  │  }                                                               │        │
│  └────────┬──────────────────────────────────────────────┬─────────┘        │
│           │                                               │                  │
│           ↓                                               ↓                  │
│  ┌────────────────────┐                       ┌──────────────────────┐     │
│  │ receive_messages() │                       │ consume_events()      │     │
│  │ (Producer)         │                       │ (Consumer)            │     │
│  │                    │                       │                       │     │
│  │ Recibe del cliente:│                       │ Lee de queue:         │     │
│  │ - user_message     │                       │ - token_chunk         │     │
│  │ - abort            │                       │ - completed           │     │
│  │                    │                       │ - interrupted         │     │
│  │ ↓                  │                       │ ↓                     │     │
│  │ process_user_      │                       │ ws.send_json(event)   │     │
│  │ message()          │                       │                       │     │
│  └────────┬───────────┘                       └───────────────────────┘     │
│           │                                                                  │
│           ↓                                                                  │
│  ┌────────────────────────────────────────────────────────────┐            │
│  │ stream_agent_response(session_id, user_input, message_id)  │            │
│  │                                                              │            │
│  │ ┌──────────────────────────────────────────────────┐       │            │
│  │ │ LangGraph Integration                             │       │            │
│  │ │                                                    │       │            │
│  │ │ graph = get_agent_graph()                         │       │            │
│  │ │                                                    │       │            │
│  │ │ async for event in graph.astream_events(          │       │            │
│  │ │   {"messages": [{"role": "user", ...}]},          │       │            │
│  │ │   config={"configurable": {"thread_id": sess}}    │       │            │
│  │ │ ):                                                 │       │            │
│  │ │   if event["event"] == "on_chat_model_stream":    │       │            │
│  │ │     delta = event["data"]["chunk"].content        │       │            │
│  │ │                                                    │       │            │
│  │ │     await session_manager.broadcast_to_session(   │       │            │
│  │ │       session_id,                                  │       │            │
│  │ │       {                                            │       │            │
│  │ │         "type": "token_chunk",                     │       │            │
│  │ │         "delta": delta,                            │       │            │
│  │ │         "message_id": message_id                   │       │            │
│  │ │       }                                            │       │            │
│  │ │     )                                              │       │            │
│  │ └──────────────────────────────────────────────────┘       │            │
│  └─────────────────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Diagrama 2: Secuencia de Abort

```
Cliente                Manager                  Agent Task              DB
  │                      │                          │                    │
  │  {type: "abort"}     │                          │                    │
  ├─────────────────────>│                          │                    │
  │                      │                          │                    │
  │                      │  abort_generation()      │                    │
  │                      │  ├──> task.cancel()      │                    │
  │                      │  │                       │                    │
  │                      │  │    ┌─────────────────>│                    │
  │                      │  │    │ asyncio.          │                    │
  │                      │  │    │ CancelledError    │                    │
  │                      │  │    │                  │                    │
  │                      │  │    │ except:           │                    │
  │                      │  │    │   save_partial()  │                    │
  │                      │  │    │                  ├───────────────────>│
  │                      │  │    │                  │ UPDATE messages    │
  │                      │  │    │                  │ SET status =       │
  │                      │  │    │                  │ 'interrupted'      │
  │                      │  │    │                  │ WHERE id = ...     │
  │                      │  │    │                  │<───────────────────┤
  │                      │  │    │                  │                    │
  │                      │  │    └──re-raise────────│                    │
  │                      │  │                       X                    │
  │                      │  │                                             │
  │                      │  └──> return message_id  │                    │
  │                      │                          │                    │
  │                      │  broadcast_to_session({  │                    │
  │                      │    type: "interrupted",  │                    │
  │                      │    message_id: ...,      │                    │
  │                      │    reason: "user_abort"  │                    │
  │                      │  })                      │                    │
  │                      │  │                       │                    │
  │                      │  ├──> Queue 1 ← event    │                    │
  │                      │  ├──> Queue 2 ← event    │                    │
  │                      │  └──> Queue 3 ← event    │                    │
  │                      │                          │                    │
  │  {type:              │                          │                    │
  │   "interrupted"}     │                          │                    │
  │<─────────────────────┤                          │                    │
  │                      │                          │                    │
  │  UI: Marcar mensaje  │                          │                    │
  │  con badge           │                          │                    │
  │  [Interrumpido]      │                          │                    │
  │                      │                          │                    │
```

---

## 🔄 Diagrama 3: Pub/Sub Multi-Observador

```
                         ChatSessionManager
                      (session_id: "session_123")
                                 │
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                       │
          │                      │                       │
    ┌─────▼─────┐          ┌────▼────┐          ┌──────▼─────┐
    │  Queue 1  │          │ Queue 2 │          │  Queue 3   │
    │  maxsize  │          │ maxsize │          │  maxsize   │
    │    100    │          │   100   │          │    100     │
    └─────┬─────┘          └────┬────┘          └──────┬─────┘
          │                     │                       │
          ↓                     ↓                       ↓
    ┌───────────┐          ┌──────────┐          ┌───────────┐
    │    WS 1   │          │   WS 2   │          │    WS 3   │
    │  conn_abc │          │ conn_def │          │  conn_ghi │
    └─────┬─────┘          └────┬─────┘          └─────┬─────┘
          │                     │                       │
          ↓                     ↓                       ↓
    ┌───────────┐          ┌──────────┐          ┌───────────┐
    │  Usuario  │          │Supervisor│          │ Dashboard │
    │ (activo)  │          │(observa) │          │ (monitor) │
    └───────────┘          └──────────┘          └───────────┘


    ┌──────────────────────────────────────────────────────┐
    │  PRODUCTOR ÚNICO (asyncio.Task)                      │
    │                                                       │
    │  async for event in graph.astream_events(...):       │
    │    delta = event["data"]["chunk"].content            │
    │                                                       │
    │    await session_manager.broadcast_to_session(       │
    │      session_id,                                     │
    │      {                                               │
    │        "type": "token_chunk",                        │
    │        "delta": delta,                               │
    │        "message_id": message_id                      │
    │      }                                               │
    │    )                                                 │
    │    ↓                                                 │
    │    Encola en Queue 1, Queue 2, Queue 3              │
    └──────────────────────────────────────────────────────┘

GARANTÍA: 1 llamada a LangGraph, N WebSockets reciben el mismo stream
```

---

## 🔐 Diagrama 4: Autenticación JWT

```
┌──────────────────────────────────────────────────────────────┐
│  CLIENTE                                                      │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  const { jwtToken } = useAuth();                             │
│                                                               │
│  const ws = new WebSocket(                                   │
│    `ws://host/ws/chat/session_123?token=${jwtToken}`         │
│  );                                                           │
│                                                               │
│  ↓                                                            │
│  GET /ws/chat/session_123?token=eyJhbGciOiJIUzI1NiIs...      │
│  Upgrade: websocket                                          │
│  Connection: Upgrade                                         │
│                                                               │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ↓
┌──────────────────────────────────────────────────────────────┐
│  SERVIDOR (FastAPI)                                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  @router.websocket("/chat/{session_id}")                     │
│  async def websocket_chat_endpoint(                          │
│    websocket: WebSocket,                                     │
│    session_id: str,                                          │
│    token: Optional[str] = Query(None)  ← Query param        │
│  ):                                                           │
│    # 1. Verificar token                                      │
│    try:                                                       │
│      user_id = await verify_jwt_token(token)                 │
│    except HTTPException as e:                                │
│      await websocket.close(code=1008)  ← Rechazar            │
│      return                                                   │
│                                                               │
│    # 2. Token válido → Aceptar conexión                      │
│    await websocket.accept()                                  │
│                                                               │
│    # 3. Registrar en SessionManager                          │
│    await session_manager.connect(                            │
│      websocket, session_id, connection_id                    │
│    )                                                          │
│                                                               │
└──────────────────────────────────────────────────────────────┘

NOTA: EventSource nativa NO permite headers personalizados,
por eso WebSocket usa query string para JWT
```

---

## 📊 Diagrama 5: Estados de Mensaje

```
┌──────────────────────────────────────────────────────────┐
│                   CICLO DE VIDA DEL MENSAJE               │
└──────────────────────────────────────────────────────────┘

    ┌───────────────┐
    │ USER_MESSAGE  │ (usuario envía)
    │ status: N/A   │
    └───────┬───────┘
            │
            ↓
    ┌───────────────┐
    │  STREAMING    │ (asistente generando)
    │ status:       │
    │ "streaming"   │ ← cursor parpadeante
    └───────┬───────┘
            │
            ├──────── Normal Flow ──────┐
            │                            │
            ↓                            ↓
    ┌───────────────┐          ┌────────────────┐
    │  COMPLETED    │          │  INTERRUPTED   │
    │ status:       │          │ status:        │
    │ "completed"   │          │ "interrupted"  │
    │               │          │                │
    │ (generación   │          │ (abort signal  │
    │  terminó)     │          │  recibida)     │
    └───────────────┘          └────────┬───────┘
                                        │
                                        ↓
                               ┌────────────────┐
                               │   PRESERVED    │
                               │                │
                               │ - Contenido    │
                               │   parcial      │
                               │   guardado     │
                               │ - Badge UI:    │
                               │  [Interrumpido]│
                               │ - Fondo        │
                               │   amarillo     │
                               └────────────────┘

CRÍTICO: Mensaje interrumpido NUNCA se borra
```

---

## 🔄 Diagrama 6: Reconexión con Rehidratación

```
┌─────────────────────────────────────────────────────────────┐
│  TIMELINE: Desconexión y Reconexión                         │
└─────────────────────────────────────────────────────────────┘

t=0     Cliente conectado, sesión activa
        │
        │  {type: "user_message", content: "Pregunta 1"}
        ↓
t=1     Asistente generando respuesta...
        │
        │  {type: "token_chunk", delta: "Hola"}
        │  {type: "token_chunk", delta: ","}
        │  {type: "token_chunk", delta: " la"}
        ↓
t=2     ⚠️  CONEXIÓN PERDIDA (red caída)
        │
        │   wsRef.current.onclose → fired
        │   setStatus('disconnected')
        │   scheduleReconnect()
        │
        ↓
t=3     🔄 Backoff: Esperando 1 segundo...
        │
        ↓
t=4     🔄 Intento reconexión #1
        │
        │   new WebSocket(url + "?token=" + jwt)
        │   ✅ Conexión exitosa
        │
        ↓
t=5     📥 REHIDRATACIÓN
        │
        │   Servidor envía:
        │   {
        │     type: "history",
        │     session_id: "session_123",
        │     messages: [
        │       {
        │         message_id: "msg_001",
        │         role: "user",
        │         content: "Pregunta 1",
        │         status: "completed"
        │       },
        │       {
        │         message_id: "msg_002",
        │         role: "assistant",
        │         content: "Hola, la respuesta es...",
        │         status: "completed"  ← Completó mientras desconectado
        │       }
        │     ]
        │   }
        │
        ↓
t=6     ✅ Cliente sincronizado
        │
        │   setMessages(history.messages)
        │   Usuario ve historial completo
        │   Puede continuar conversación
        │
        └──> LISTO PARA NUEVOS MENSAJES
```

---

## 🎨 Diagrama 7: UI States (Frontend)

```
┌──────────────────────────────────────────────────────────────┐
│  ESTADOS DE LA INTERFAZ                                       │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  STATUS: 'disconnected'                                      │
├─────────────────────────────────────────────────────────────┤
│  Header: 🔴 Desconectado                                     │
│  Input:  [Deshabilitado - placeholder: "Conectando..."]     │
│  Button: [Deshabilitado]                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  STATUS: 'connecting'                                        │
├─────────────────────────────────────────────────────────────┤
│  Header: 🟡 Conectando...                                    │
│  Input:  [Deshabilitado]                                     │
│  Button: [Deshabilitado]                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  STATUS: 'connected', GENERATION_STATUS: 'idle'              │
├─────────────────────────────────────────────────────────────┤
│  Header: 🟢 Conectado                                        │
│  Input:  [Habilitado - placeholder: "Escribe..."]           │
│  Button: [Habilitado]                                        │
│  Abort:  [Oculto]                                            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  STATUS: 'connected', GENERATION_STATUS: 'generating'        │
├─────────────────────────────────────────────────────────────┤
│  Header: 🟢 Conectado  │  ⏳ Generando...                    │
│  Input:  [Habilitado]  ← Puede interrumpir                  │
│  Button: [Habilitado]                                        │
│  Abort:  [⏹ Detener respuesta]  ← VISIBLE                   │
│                                                               │
│  Último mensaje:                                             │
│  ┌────────────────────────────────────────────────┐         │
│  │ 🤖 Asistente    [⚡ escribiendo...]             │         │
│  │ ┌────────────────────────────────────────────┐ │         │
│  │ │ Hola, soy el asistente de Brasaland│       │ │         │
│  │ └────────────────────────────────────────────┘ │         │
│  │ 12:34                                          │         │
│  └────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  STATUS: 'connected', GENERATION_STATUS: 'interrupted'       │
├─────────────────────────────────────────────────────────────┤
│  Mensaje interrumpido:                                       │
│  ┌────────────────────────────────────────────────┐         │
│  │ 🤖 Asistente    [[Interrumpido]]               │         │
│  │ ┌────────────────────────────────────────────┐ │         │
│  │ │ Hola, soy el asistente de Brasa             │ │ ← Parcial
│  │ └────────────────────────────────────────────┘ │         │
│  │ 12:34                                          │         │
│  └────────────────────────────────────────────────┘         │
│                                                               │
│  ⚠️  Fondo amarillo + borde izquierdo amarillo              │
│  ✅  Contenido preservado                                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  STATUS: 'reconnecting'                                      │
├─────────────────────────────────────────────────────────────┤
│  Header: 🟡 Reconectando... (3)  ← intento #3               │
│  Input:  [Deshabilitado]                                     │
│  Button: [Deshabilitado]                                     │
│  Messages: [Preservados en estado]                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Checklist de Implementación

- [x] Router WebSocket con endpoint `/ws/chat/{session_id}`
- [x] Autenticación JWT via query string
- [x] `ChatSessionManager` con Pub/Sub
- [x] Abort genuino (`asyncio.Task.cancel()`)
- [x] Preservación de mensajes interrumpidos
- [x] React hook `useChatWebSocket`
- [x] React component `ChatWebSocket`
- [x] CSS con estados visuales (streaming, interrumpido)
- [x] Reconexión con backoff exponencial
- [x] Rehidratación de historial
- [x] 15 tests automatizados

---

**Firmado**: Senior Solutions Architect  
**Fecha**: 2026-10-31

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
