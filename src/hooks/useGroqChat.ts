"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChatMessage, ChatSession, ChatSettings } from "@/types/chat";

interface ChatApiResponse {
  content: string;
  model: string;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

interface UseGroqChatResult {
  sessions: ChatSession[];
  activeSession: ChatSession | null;
  activeSessionId: string | null;
  isThinking: boolean;
  settings: ChatSettings;
  createNewChat: () => void;
  setActiveSessionId: (sessionId: string) => void;
  updateSettings: (next: Partial<ChatSettings>) => void;
  sendMessage: (rawContent: string) => Promise<void>;
  totalTokens: number;
  averageLatency: number;
  requestsCount: number;
  lastError: string | null;
}

const STORAGE_KEY = "dev-ai-console:sessions";
const ACTIVE_STORAGE_KEY = "dev-ai-console:active-session";

function makeSession(index: number): ChatSession {
  return {
    id: crypto.randomUUID(),
    title: `New Chat ${index}`,
    createdAt: Date.now(),
    messages: [],
  };
}

function appendMessage(sessions: ChatSession[], sessionId: string, message: ChatMessage) {
  return sessions.map((session) => {
    if (session.id !== sessionId) {
      return session;
    }

    const isFirstUserMessage = session.messages.length === 0 && message.role === "user";

    return {
      ...session,
      title: isFirstUserMessage ? message.content.slice(0, 30) || session.title : session.title,
      messages: [...session.messages, message],
    };
  });
}

export function useGroqChat(): UseGroqChatResult {
  const [sessions, setSessions] = useState<ChatSession[]>(() => [makeSession(1)]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [settings, setSettings] = useState<ChatSettings>({
    temperature: 0.7,
    topP: 0.9,
    jsonMode: false,
  });
  const [isThinking, setIsThinking] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const isHydrated = useRef(false);

  useEffect(() => {
    try {
      const rawSessions = localStorage.getItem(STORAGE_KEY);
      const rawActive = localStorage.getItem(ACTIVE_STORAGE_KEY);
      const parsed = rawSessions ? (JSON.parse(rawSessions) as ChatSession[]) : [];

      if (parsed.length > 0) {
        setSessions(parsed);
        setActiveSessionId(rawActive && parsed.some((x) => x.id === rawActive) ? rawActive : parsed[0].id);
      } else {
        const first = makeSession(1);
        setSessions([first]);
        setActiveSessionId(first.id);
      }
    } catch {
      const fallback = makeSession(1);
      setSessions([fallback]);
      setActiveSessionId(fallback.id);
    } finally {
      isHydrated.current = true;
    }
  }, []);

  useEffect(() => {
    if (!isHydrated.current) {
      return;
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    if (activeSessionId) {
      localStorage.setItem(ACTIVE_STORAGE_KEY, activeSessionId);
    }
  }, [sessions, activeSessionId]);

  const createNewChat = useCallback(() => {
    setSessions((prev) => {
      const next = makeSession(prev.length + 1);
      setActiveSessionId(next.id);
      return [...prev, next];
    });
    setLastError(null);
  }, []);

  const updateSettings = useCallback((next: Partial<ChatSettings>) => {
    setSettings((prev) => ({ ...prev, ...next }));
  }, []);

  const sendMessage = useCallback(
    async (rawContent: string) => {
      const content = rawContent.trim();
      if (!content || !activeSessionId || isThinking) {
        return;
      }

      setLastError(null);

      const activeBefore = sessions.find((session) => session.id === activeSessionId);
      if (!activeBefore) {
        return;
      }

      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        createdAt: Date.now(),
      };

      const requestMessages = [...activeBefore.messages, userMessage].map((message) => ({
        role: message.role,
        content: message.content,
      }));

      setSessions((prev) => appendMessage(prev, activeSessionId, userMessage));
      setIsThinking(true);

      const startedAt = performance.now();

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            messages: requestMessages,
            temperature: settings.temperature,
            top_p: settings.topP,
            json_mode: settings.jsonMode,
            stream: false,
          }),
        });

        const data = (await response.json()) as ChatApiResponse | { error: string };

        if (!response.ok || "error" in data) {
          const apiError = "error" in data ? data.error : "Unexpected error from /api/chat";
          throw new Error(apiError);
        }

        const endedAt = performance.now();
        const latencySeconds = Number(((endedAt - startedAt) / 1000).toFixed(2));

        const assistantMessage: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: data.content,
          createdAt: Date.now(),
          usage: {
            promptTokens: data.usage.prompt_tokens,
            completionTokens: data.usage.completion_tokens,
            totalTokens: data.usage.total_tokens,
            latencySeconds,
            model: data.model,
          },
        };

        setSessions((prev) => appendMessage(prev, activeSessionId, assistantMessage));
      } catch (error) {
        const message = error instanceof Error ? error.message : "No se pudo consultar Groq en este momento.";
        setLastError(message);

        const fallbackMessage: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `Error de integración Groq: ${message}`,
          createdAt: Date.now(),
          usage: {
            promptTokens: 0,
            completionTokens: 0,
            totalTokens: 0,
            latencySeconds: 0,
            model: "llama-3.3-70b-versatile",
          },
        };

        setSessions((prev) => appendMessage(prev, activeSessionId, fallbackMessage));
      } finally {
        setIsThinking(false);
      }
    },
    [activeSessionId, isThinking, sessions, settings],
  );

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? null,
    [sessions, activeSessionId],
  );

  const metrics = useMemo(() => {
    if (!activeSession) {
      return { totalTokens: 0, averageLatency: 0, requestsCount: 0 };
    }

    const withUsage = activeSession.messages.filter((message) => message.usage);
    const totals = withUsage.reduce(
      (acc, message) => {
        const usage = message.usage;
        if (!usage) {
          return acc;
        }

        return {
          tokens: acc.tokens + usage.totalTokens,
          latency: acc.latency + usage.latencySeconds,
          count: acc.count + 1,
        };
      },
      { tokens: 0, latency: 0, count: 0 },
    );

    return {
      totalTokens: totals.tokens,
      averageLatency: totals.count > 0 ? totals.latency / totals.count : 0,
      requestsCount: totals.count,
    };
  }, [activeSession]);

  return {
    sessions,
    activeSession,
    activeSessionId,
    isThinking,
    settings,
    createNewChat,
    setActiveSessionId,
    updateSettings,
    sendMessage,
    totalTokens: metrics.totalTokens,
    averageLatency: metrics.averageLatency,
    requestsCount: metrics.requestsCount,
    lastError,
  };
}
