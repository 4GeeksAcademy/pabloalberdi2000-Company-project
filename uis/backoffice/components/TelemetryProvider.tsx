"use client";

/**
 * Telemetry Provider - Wrapper para instrumentación global
 *
 * Inicializa:
 * 1. Page view tracking (automático en cada cambio de ruta)
 * 2. Error tracking global (window.onerror, unhandledrejection)
 * 3. Performance monitoring (opcional)
 *
 * Uso en layout.tsx:
 * ```tsx
 * <TelemetryProvider>
 *   <ErrorBoundary>
 *     {children}
 *   </ErrorBoundary>
 * </TelemetryProvider>
 * ```
 */

import { ReactNode, useEffect } from "react";
import { usePageViewTracking } from "@/lib/telemetry-hooks";
import { track } from "@/lib/telemetry";

interface Props {
  children: ReactNode;
}

export function TelemetryProvider({ children }: Props) {
  // Auto-track page views
  usePageViewTracking();

  useEffect(() => {
    // Global error handler (window.onerror)
    const handleError = (
      message: string | Event,
      source?: string,
      lineno?: number,
      colno?: number,
      error?: Error
    ) => {
      track("frontend_error_uncaught", {
        error_message: typeof message === "string" ? message : error?.message || "Unknown error",
        error_name: error?.name || "Error",
        error_stack: error?.stack ? sanitizeStackTrace(error.stack) : "",
        source_file: source || "",
        line_number: lineno || null,
        column_number: colno || null,
        page_url: window.location.href,
      });

      // No retornar true para permitir que el navegador también loguee
      return false;
    };

    // Unhandled promise rejections
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      track("frontend_error_uncaught", {
        error_message: event.reason?.message || String(event.reason),
        error_name: "UnhandledPromiseRejection",
        error_stack: event.reason?.stack ? sanitizeStackTrace(event.reason.stack) : "",
        source_file: "",
        page_url: window.location.href,
      });
    };

    window.addEventListener("error", handleError);
    window.addEventListener("unhandledrejection", handleUnhandledRejection);

    return () => {
      window.removeEventListener("error", handleError);
      window.removeEventListener("unhandledrejection", handleUnhandledRejection);
    };
  }, []);

  return <>{children}</>;
}

/**
 * Sanitiza stack trace para remover paths locales.
 */
function sanitizeStackTrace(stack: string): string {
  return stack
    .replace(/\/Users\/[^/]+\//g, "[PROJECT_ROOT]/")
    .replace(/C:\\Users\\[^\\]+\\/g, "[PROJECT_ROOT]\\")
    .replace(/file:\/\/\/[^\s]+/g, "[PROJECT_ROOT]");
}
