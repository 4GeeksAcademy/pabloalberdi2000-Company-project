"use client";

import { useChatConsole } from "@/components/chat/ChatConsoleContext";

export function Sidebar() {
  const { sessions, activeSessionId, setActiveSessionId, createNewChat } = useChatConsole();

  return (
    <aside className="glass-panel inner-glow-primary flex h-[calc(100vh-2rem)] w-full flex-col rounded-3xl p-4 shadow-panel md:max-w-72">
      <button
        type="button"
        onClick={createNewChat}
        className="mb-4 rounded-xl bg-primary/90 px-4 py-3 text-title-sm text-slate-950 transition hover:bg-primary"
      >
        New Chat
      </button>

      <p className="mb-2 px-1 text-xs font-medium uppercase tracking-[0.2em] text-on-surface-variant">Sessions</p>

      <div className="space-y-2 overflow-y-auto pr-1">
        {sessions.map((session) => {
          const isActive = session.id === activeSessionId;

          return (
            <button
              key={session.id}
              type="button"
              onClick={() => setActiveSessionId(session.id)}
              className={`w-full rounded-xl px-3 py-2 text-left text-sm transition ${
                isActive
                  ? "bg-tertiary-container text-on-surface"
                  : "bg-surface-container-low text-on-surface-variant hover:bg-surface-container"
              }`}
            >
              <p className="truncate font-medium">{session.title}</p>
              <p className="text-xs text-on-surface-variant">{session.messages.length} messages</p>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
