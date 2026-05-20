"use client";

import { createContext, useContext, type ReactNode } from "react";
import { useGroqChat } from "@/hooks/useGroqChat";
import type { ChatSession, ChatSettings } from "@/types/chat";

interface ChatConsoleContextValue {
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

const ChatConsoleContext = createContext<ChatConsoleContextValue | null>(null);

export function ChatConsoleProvider({ children }: { children: ReactNode }) {
  const value = useGroqChat();

  return <ChatConsoleContext.Provider value={value}>{children}</ChatConsoleContext.Provider>;
}

export function useChatConsole() {
  const context = useContext(ChatConsoleContext);
  if (!context) {
    throw new Error("useChatConsole must be used inside ChatConsoleProvider");
  }

  return context;
}
