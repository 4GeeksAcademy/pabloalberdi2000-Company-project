"use client";

import { useChatConsole } from "@/components/chat/ChatConsoleContext";

export function AnalyticsPanel() {
  const { totalTokens, averageLatency, requestsCount, activeSession } = useChatConsole();

  return (
    <aside className="glass-panel inner-glow-primary h-[calc(100vh-2rem)] rounded-3xl p-4 shadow-panel lg:w-80">
      <h2 className="text-title-sm uppercase tracking-[0.2em] text-on-surface-variant">Session Metrics</h2>
      <p className="mt-1 text-body-md text-on-surface">{activeSession?.title ?? "No active session"}</p>

      <div className="mt-4 space-y-3">
        <article className="rounded-xl bg-surface-container-low p-3">
          <p className="text-xs uppercase tracking-[0.16em] text-on-surface-variant">Total Tokens</p>
          <p className="mt-1 text-2xl font-semibold text-on-surface">{totalTokens.toLocaleString()}</p>
          <p className="text-code-md text-on-surface-variant">Σ(prompt + completion)</p>
        </article>

        <article className="rounded-xl bg-surface-container-low p-3">
          <p className="text-xs uppercase tracking-[0.16em] text-on-surface-variant">Average Latency</p>
          <p className="mt-1 text-2xl font-semibold text-on-surface">{averageLatency.toFixed(2)}s</p>
          <p className="text-code-md text-on-surface-variant">mean(response time)</p>
        </article>

        <article className="rounded-xl bg-surface-container-low p-3">
          <p className="text-xs uppercase tracking-[0.16em] text-on-surface-variant">Requests Counter</p>
          <p className="mt-1 text-2xl font-semibold text-on-surface">{requestsCount}</p>
          <p className="text-code-md text-on-surface-variant">assistant turns</p>
        </article>
      </div>
    </aside>
  );
}
