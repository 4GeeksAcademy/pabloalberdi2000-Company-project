"use client";

import { useState, useEffect, useRef } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useRouter } from "next/navigation";
import { Send, Loader2, AlertCircle, Bot, User, StopCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";

/**
 * Página de Chat WebSocket con Streaming
 *
 * Características:
 * - WebSocket bidireccional con streaming token por token
 * - Auto-scroll a nuevos mensajes
 * - Indicador de escritura en tiempo real
 * - Abort de generación
 * - Reconexión automática
 * - Historial de mensajes
 */

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "completed" | "interrupted" | "generating";
  timestamp: string;
}

export default function ChatPage() {
  const { token, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentMessageId, setCurrentMessageId] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const sessionId = useRef(`session_${Date.now()}`);
  const isConnectingRef = useRef(false);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Debug: Log messages state changes
  useEffect(() => {
    console.log("🔄 Messages state updated. Total:", messages.length, messages);
  }, [messages]);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  // WebSocket connection
  useEffect(() => {
    if (!isAuthenticated || !token) return;

    // Prevenir conexiones duplicadas (React 18 StrictMode ejecuta useEffect 2 veces)
    if (isConnectingRef.current) {
      console.log("⚠️ Ya se está estableciendo una conexión, ignorando duplicado");
      return;
    }

    // Prevenir si ya hay conexión activa
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log("⚠️ Ya hay una conexión WebSocket activa");
      return;
    }

    // Cerrar conexión anterior si existe
    if (wsRef.current) {
      console.log("🔌 Cerrando conexión WebSocket anterior");
      wsRef.current.close();
      wsRef.current = null;
    }

    isConnectingRef.current = true;

    // Usar EXTERNAL_API_URL para conexiones desde el navegador
    const API_BASE = process.env.NEXT_PUBLIC_EXTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const WS_BASE = API_BASE.replace('http://', 'ws://').replace('https://', 'wss://');
    const wsUrl = `${WS_BASE}/ws/chat/${sessionId.current}?token=${token}`;

    console.log("🔌 Conectando a WebSocket:", wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("✅ WebSocket conectado");
      setIsConnected(true);
      setError(null);
      isConnectingRef.current = false;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("📨 Mensaje recibido:", data);

        switch (data.type) {
          case "history":
            // Cargar historial
            if (data.messages && data.messages.length > 0) {
              setMessages(data.messages.map((msg: any) => ({
                id: msg.message_id,
                role: msg.role,
                content: msg.content,
                status: msg.status,
                timestamp: msg.created_at
              })));
            }
            break;

          case "token_chunk":
            // Streaming: agregar delta al mensaje actual
            setIsGenerating(true);
            setCurrentMessageId(data.message_id);

            setMessages((prev) => {
              console.log("📝 Actualizando mensajes. Total actual:", prev.length);
              const existing = prev.find((m) => m.id === data.message_id);

              if (existing) {
                // Actualizar contenido
                console.log("✏️ Actualizando mensaje existente:", data.message_id);
                return prev.map((m) =>
                  m.id === data.message_id
                    ? { ...m, content: m.content + data.delta }
                    : m
                );
              } else {
                // Crear nuevo mensaje
                console.log("➕ Creando nuevo mensaje del asistente:", data.message_id);
                return [
                  ...prev,
                  {
                    id: data.message_id,
                    role: "assistant",
                    content: data.delta,
                    status: "generating",
                    timestamp: data.timestamp
                  }
                ];
              }
            });
            break;

          case "generation_completed":
            // Generación completada
            setIsGenerating(false);
            setCurrentMessageId(null);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === data.message_id
                  ? { ...m, status: "completed" }
                  : m
              )
            );
            break;

          case "generation_interrupted":
            // Generación interrumpida
            setIsGenerating(false);
            setCurrentMessageId(null);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === data.message_id
                  ? { ...m, status: "interrupted" }
                  : m
              )
            );
            break;

          case "error":
            setError(data.message);
            setIsGenerating(false);
            setCurrentMessageId(null);
            break;
        }
      } catch (err) {
        console.error("Error procesando mensaje WS:", err);
      }
    };

    ws.onerror = (event) => {
      console.error("❌ WebSocket error:", event);
      setError("Error de conexión con el servidor");
      setIsConnected(false);
      isConnectingRef.current = false;
    };

    ws.onclose = (event) => {
      console.log("🔌 WebSocket cerrado:", event.code, event.reason);
      setIsConnected(false);
      setIsGenerating(false);
      isConnectingRef.current = false;

      // Reconexión automática después de 3 segundos
      if (event.code !== 1000 && event.code !== 1008) {
        setTimeout(() => {
          console.log("🔄 Intentando reconectar...");
        }, 3000);
      }
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close(1000, "Component unmounted");
      }
    };
  }, [isAuthenticated, token]);

  const handleSendMessage = () => {
    if (!inputValue.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    const userMessageId = `msg_${Date.now()}`;

    // Agregar mensaje del usuario localmente
    const userMessage: Message = {
      id: userMessageId,
      role: "user",
      content: inputValue.trim(),
      status: "completed",
      timestamp: new Date().toISOString()
    };

    console.log("📤 Agregando mensaje del usuario:", userMessage);
    setMessages((prev) => {
      const newMessages = [...prev, userMessage];
      console.log("📋 Total mensajes después de agregar:", newMessages.length);
      return newMessages;
    });

    // Enviar a WebSocket
    wsRef.current.send(
      JSON.stringify({
        type: "user_message",
        content: inputValue.trim(),
        message_id: userMessageId
      })
    );

    setInputValue("");
    setError(null);
  };

  const handleAbort = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "abort" }));
      setIsGenerating(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between max-w-5xl mx-auto">
          <div className="flex items-center gap-3">
            <Bot className="w-8 h-8 text-primary" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Asistente Brasaland
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {isConnected ? "🟢 Conectado" : "🔴 Desconectado"}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <Bot className="w-16 h-16 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
              <p className="text-gray-600 dark:text-gray-400 text-lg">
                ¡Hola! Soy el asistente de Brasaland
              </p>
              <p className="text-gray-500 dark:text-gray-500 text-sm mt-2">
                Pregúntame sobre operaciones, candidatos, inventario o incidencias
              </p>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-3 ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {message.role === "assistant" && (
                <div className="flex-shrink-0 w-8 h-8 bg-primary rounded-full flex items-center justify-center">
                  <Bot className="w-5 h-5 text-white" />
                </div>
              )}

              <div
                className={`max-w-2xl rounded-lg px-4 py-3 shadow-md ${
                  message.role === "user"
                    ? "bg-gradient-to-r from-blue-500 to-blue-600 text-white"
                    : "bg-white dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-200 dark:border-gray-600"
                }`}
              >
                {message.role === "user" ? (
                  <p className="whitespace-pre-wrap leading-relaxed">
                    {message.content}
                  </p>
                ) : (
                  <div className="prose prose-sm dark:prose-invert max-w-none [&>*]:text-gray-900 [&>*]:dark:text-white">
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                        ul: ({ children }) => <ul className="list-disc ml-4 mb-2">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal ml-4 mb-2">{children}</ol>,
                        li: ({ children }) => <li className="mb-1">{children}</li>,
                        strong: ({ children }) => <strong className="font-bold">{children}</strong>,
                        code: ({ children }) => (
                          <code className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded text-sm">
                            {children}
                          </code>
                        ),
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                )}

                {message.status === "interrupted" && (
                  <p className="text-xs mt-2 opacity-70 italic">
                    (Respuesta interrumpida)
                  </p>
                )}

                {message.status === "generating" && (
                  <span className="inline-block w-2 h-4 bg-current animate-pulse ml-1"></span>
                )}
              </div>

              {message.role === "user" && (
                <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-blue-500 to-blue-600 rounded-full flex items-center justify-center shadow-md">
                  <User className="w-5 h-5 text-white" />
                </div>
              )}
            </div>
          ))}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="px-4 py-2 bg-red-50 dark:bg-red-900/20 border-t border-red-200 dark:border-red-800">
          <div className="max-w-4xl mx-auto flex items-center gap-2 text-red-700 dark:text-red-400">
            <AlertCircle className="w-4 h-4" />
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-4 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-2">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                isConnected
                  ? "Escribe tu mensaje... (Enter para enviar, Shift+Enter para nueva línea)"
                  : "Conectando..."
              }
              disabled={!isConnected || isGenerating}
              className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 resize-none"
              rows={2}
            />

            {isGenerating ? (
              <button
                onClick={handleAbort}
                className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 focus:ring-2 focus:ring-red-600 focus:ring-offset-2 flex items-center gap-2 transition-colors"
              >
                <StopCircle className="w-5 h-5" />
                Detener
              </button>
            ) : (
              <button
                onClick={handleSendMessage}
                disabled={!isConnected || !inputValue.trim()}
                className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
              >
                <Send className="w-5 h-5" />
                Enviar
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
