/**
 * Telemetry Hooks - Instrumentación de Navegación y Performance
 *
 * Hooks reutilizables para tracking de eventos transversales:
 * - Page views (navegación)
 * - Auth events (login, logout, session expiry)
 * - Performance (Web Vitals)
 */

"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { track } from "./telemetry";

// ============================================================
// Navigation Tracking
// ============================================================

/**
 * Hook para tracking automático de page views.
 *
 * Registra un evento `page_view` cada vez que cambia la ruta.
 * Incluye metadata útil: referrer, viewport, tiempo de carga.
 *
 * Uso:
 * ```tsx
 * // En layout.tsx o páginas individuales
 * export default function RootLayout({ children }) {
 *   usePageViewTracking();
 *   return <html>...</html>;
 * }
 * ```
 *
 * @param samplingRate - Porcentaje de eventos a registrar (default 10%)
 */
export function usePageViewTracking(samplingRate = 0.1): void {
  const pathname = usePathname();
  const previousPathname = useRef<string | null>(null);

  useEffect(() => {
    // Skip en SSR
    if (typeof window === "undefined") return;

    // Skip si es la misma ruta (evitar duplicados en re-renders)
    if (previousPathname.current === pathname) return;
    previousPathname.current = pathname;

    // Sampling (10% by default según TELEMETRY_PLAN.md)
    if (Math.random() > samplingRate) return;

    // Metadata de navegación
    const metadata = {
      page_name: pathname,
      referrer: document.referrer || null,
      viewport_width: window.innerWidth,
      viewport_height: window.innerHeight,
      user_agent: navigator.userAgent,
      language: navigator.language,
    };

    track("page_view", metadata);
  }, [pathname, samplingRate]);
}

// ============================================================
// Auth Tracking
// ============================================================

/**
 * Track login attempt failed.
 *
 * IMPORTANTE: NUNCA loguear email o password en claro.
 * Solo loguear failure_reason genérico.
 *
 * @param failureReason - Razón del fallo (enum: invalid_credentials, account_locked, network_error)
 * @param emailHash - SHA256 hash del email (opcional, para detección de ataques)
 */
export function trackLoginFailed(
  failureReason: "invalid_credentials" | "account_locked" | "network_error",
  emailHash?: string
): void {
  track("login_attempt_failed", {
    failure_reason: failureReason,
    email_hash: emailHash || null,
    ip_address_masked: null, // Backend lo enriquece
  });
}

/**
 * Track login successful.
 *
 * @param userId - UUID del usuario autenticado
 */
export function trackLoginSuccess(userId: string): void {
  track("login_attempt_success", {
    user_id: userId,
  });
}

/**
 * Track session expiration.
 *
 * Llamar cuando el token JWT expire o cuando el usuario sea
 * deslogueado por inactividad.
 *
 * @param reason - Razón de expiración (inactivity, token_expired, manual_logout)
 */
export function trackSessionExpired(
  reason: "inactivity" | "token_expired" | "manual_logout"
): void {
  track("session_expired", {
    expiration_reason: reason,
    session_duration_seconds: null, // TODO: calcular duración
  });
}

/**
 * Track password reset request.
 *
 * Útil para detectar campañas de phishing masivo (pico anómalo >3σ).
 *
 * @param emailHash - SHA256 hash del email
 */
export function trackPasswordResetRequested(emailHash: string): void {
  track("password_reset_requested", {
    email_hash: emailHash,
  });
}

// ============================================================
// Performance Tracking (Web Vitals)
// ============================================================

/**
 * Track Core Web Vitals.
 *
 * Next.js expone las métricas vía reportWebVitals en _app.tsx.
 * Este helper las envía a telemetría.
 *
 * Uso en pages/_app.tsx:
 * ```tsx
 * export function reportWebVitals(metric: NextWebVitalsMetric) {
 *   trackWebVital(metric);
 * }
 * ```
 *
 * @param metric - Métrica de Next.js Web Vitals
 */
export function trackWebVital(metric: {
  id: string;
  name: string;
  label: string;
  value: number;
}): void {
  // Solo track métricas finales (no delta)
  if (metric.label !== "web-vital") return;

  track("web_vital_recorded", {
    metric_name: metric.name, // CLS, FID, LCP, FCP, TTFB
    metric_value: metric.value,
    metric_id: metric.id,
    page_url: typeof window !== "undefined" ? window.location.href : "",
  });
}

// ============================================================
// Network Error Tracking
// ============================================================

/**
 * Track API request failed.
 *
 * Llamar en catch de llamadas API para distinguir 4xx vs 5xx.
 *
 * @param endpoint - URL del endpoint (sin query params sensibles)
 * @param statusCode - HTTP status code
 * @param method - HTTP method
 */
export function trackApiRequestFailed(
  endpoint: string,
  statusCode: number,
  method: "GET" | "POST" | "PATCH" | "PUT" | "DELETE"
): void {
  track("api_request_failed", {
    endpoint_path: endpoint,
    http_status: statusCode,
    http_method: method,
    error_category: statusCode >= 500 ? "server_error" : "client_error",
  });
}

/**
 * Track network timeout.
 *
 * Útil para detectar problemas de CDN por región geográfica.
 *
 * @param endpoint - URL del endpoint
 * @param timeoutMs - Timeout configurado
 */
export function trackNetworkTimeout(endpoint: string, timeoutMs: number): void {
  track("network_request_timeout", {
    endpoint_path: endpoint,
    timeout_ms: timeoutMs,
  });
}
