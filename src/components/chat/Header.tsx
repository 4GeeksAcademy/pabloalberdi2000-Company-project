"use client";

import { useChatConsole } from "@/components/chat/ChatConsoleContext";

export function Header() {
  const { isThinking, settings } = useChatConsole();

  return (
    <header className="glass-panel mb-4 flex items-center justify-between rounded-2xl px-4 py-3">
      <div>
        <h1 className="text-headline-md-mobile md:text-headline-md text-on-surface">Developer AI Chat Console</h1>
        <p className="text-code-md text-on-surface-variant">Groq / Llama 3.3 / temp {settings.temperature.toFixed(2)}</p>
      </div>

      <div className="flex items-center gap-2 rounded-full bg-surface-container-low px-3 py-1.5 text-code-md text-on-surface-variant">
        <span className={`h-2.5 w-2.5 rounded-full bg-secondary ${isThinking ? "status-pulse" : ""}`} />
        {isThinking ? "Model running" : "Idle"}
      </div>
    </header>
  );
}
