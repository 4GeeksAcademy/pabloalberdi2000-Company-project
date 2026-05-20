"use client";

import { FormEvent, KeyboardEvent, useMemo, useState } from "react";
import { useChatConsole } from "@/components/chat/ChatConsoleContext";

function formatTime(value: number) {
  return new Intl.DateTimeFormat("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(value);
}

export function ChatWorkspace() {
  const { activeSession, isThinking, sendMessage, settings, updateSettings, lastError } = useChatConsole();
  const [draft, setDraft] = useState("");

  const messageList = useMemo(() => activeSession?.messages ?? [], [activeSession]);

  async function handleSend(event: FormEvent) {
    event.preventDefault();
    if (!draft.trim()) {
      return;
    }

    const outgoing = draft;
    setDraft("");
    await sendMessage(outgoing);
  }

  async function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      if (!draft.trim()) {
        return;
      }

      const outgoing = draft;
      setDraft("");
      await sendMessage(outgoing);
    }
  }

  return (
    <section className="grid h-[calc(100vh-2rem)] grid-rows-[1fr_auto] gap-4">
      <div className="glass-panel rounded-3xl p-4">
        <div className="h-full space-y-3 overflow-y-auto pr-1">
          {messageList.length === 0 && (
            <div className="rounded-2xl border border-outline-variant bg-surface-container-low p-5 text-on-surface-variant">
              Inicia una conversación con tu modelo Groq. El historial de la sesión se guardará automáticamente.
            </div>
          )}

          {messageList.map((message) => {
            const isAssistant = message.role === "assistant";

            return (
              <article
                key={message.id}
                className={`animate-slide-up rounded-2xl p-4 ${
                  isAssistant ? "bg-surface-container text-on-surface" : "bg-tertiary-container text-on-surface"
                }`}
              >
                <div className="mb-2 flex items-center justify-between text-code-md text-on-surface-variant">
                  <span>{isAssistant ? "GROQ / Llama 3" : "You"}</span>
                  <span>{formatTime(message.createdAt)}</span>
                </div>

                <p className="whitespace-pre-wrap text-body-md leading-relaxed">{message.content}</p>

                {message.usage && (
                  <p className="mt-3 text-code-md text-on-surface-variant">
                    {message.usage.promptTokens} prompt | {message.usage.completionTokens} comp | {message.usage.latencySeconds}s
                  </p>
                )}
              </article>
            );
          })}

          {lastError && (
            <div className="rounded-xl border border-danger/60 bg-danger/10 px-4 py-3 text-code-md text-danger">{lastError}</div>
          )}

          <div
            id="ai-thinking"
            className={`rounded-xl border border-outline-variant bg-surface-container-low px-4 py-3 text-code-md text-on-surface-variant ${
              isThinking ? "block" : "hidden"
            }`}
          >
            GROQ IS THINKING...
          </div>
        </div>
      </div>

      <form onSubmit={handleSend} className="glass-panel rounded-3xl p-4">
        <div className="mb-3 grid gap-4 lg:grid-cols-3">
          <label className="space-y-2 text-code-md text-on-surface-variant">
            <span>Temperature: {settings.temperature.toFixed(2)}</span>
            <input
              type="range"
              min="0"
              max="2"
              step="0.01"
              value={settings.temperature}
              onChange={(event) => updateSettings({ temperature: Number(event.target.value) })}
              className="w-full accent-primary"
            />
          </label>

          <label className="space-y-2 text-code-md text-on-surface-variant">
            <span>Top P: {settings.topP.toFixed(2)}</span>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={settings.topP}
              onChange={(event) => updateSettings({ topP: Number(event.target.value) })}
              className="w-full accent-secondary"
            />
          </label>

          <button
            type="button"
            onClick={() => updateSettings({ jsonMode: !settings.jsonMode })}
            className="flex items-center justify-between rounded-xl border border-outline-variant px-3 py-2 text-code-md text-on-surface"
          >
            <span>JSON_MODE</span>
            <span
              className={`relative h-6 w-11 rounded-full transition ${
                settings.jsonMode ? "bg-secondary" : "bg-outline-variant"
              }`}
            >
              <span
                className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition ${
                  settings.jsonMode ? "left-[1.35rem]" : "left-0.5"
                }`}
              />
            </span>
          </button>
        </div>

        <div className="flex gap-3">
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isThinking}
            placeholder="Escribe tu prompt... (Cmd/Ctrl + Enter para enviar)"
            className="min-h-24 flex-1 resize-none rounded-2xl border border-outline-variant bg-surface-container-low px-4 py-3 text-body-md text-on-surface outline-none transition focus:border-primary disabled:cursor-not-allowed disabled:opacity-60"
          />

          <button
            type="submit"
            disabled={isThinking || !draft.trim()}
            className="h-fit rounded-2xl bg-primary px-5 py-3 text-title-sm text-slate-950 transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </form>
    </section>
  );
}
