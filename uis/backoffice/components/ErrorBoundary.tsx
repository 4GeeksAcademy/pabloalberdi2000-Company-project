"use client";

/**
 * Error Boundary con Tracking de Telemetría
 *
 * Captura errores no controlados de React y:
 * 1. Registra el error en telemetría (frontend_error_uncaught)
 * 2. Muestra UI de fallback al usuario
 * 3. Permite recuperación con "Try again"
 *
 * Uso:
 * ```tsx
 * <ErrorBoundary>
 *   <YourComponent />
 * </ErrorBoundary>
 * ```
 */

import React, { Component, ErrorInfo, ReactNode } from "react";
import { track } from "@/lib/telemetry";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("❌ Uncaught error:", error, errorInfo);

    // Track error en telemetría
    track("frontend_error_uncaught", {
      error_message: error.message,
      error_name: error.name,
      error_stack: this.sanitizeStackTrace(error.stack || ""),
      component_stack: errorInfo.componentStack || "",
      page_url: typeof window !== "undefined" ? window.location.href : "",
    });
  }

  /**
   * Sanitiza stack trace para remover paths locales del desarrollador.
   * Previene PII leakage (ej. /Users/john.doe/project/).
   */
  private sanitizeStackTrace(stack: string): string {
    return stack
      .replace(/\/Users\/[^/]+\//g, "[PROJECT_ROOT]/")
      .replace(/C:\\Users\\[^\\]+\\/g, "[PROJECT_ROOT]\\")
      .replace(/file:\/\/\/[^\s]+/g, "[PROJECT_ROOT]");
  }

  private handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Fallback UI personalizado o default
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "400px",
            padding: "2rem",
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: "4rem",
              marginBottom: "1rem",
            }}
          >
            ⚠️
          </div>
          <h2
            style={{
              fontSize: "1.5rem",
              fontWeight: "600",
              marginBottom: "0.5rem",
              color: "#1f2937",
            }}
          >
            Algo salió mal
          </h2>
          <p
            style={{
              color: "#6b7280",
              marginBottom: "1.5rem",
              maxWidth: "500px",
            }}
          >
            Ocurrió un error inesperado. El equipo técnico ha sido notificado.
            Por favor, intenta nuevamente.
          </p>
          <button
            onClick={this.handleReset}
            style={{
              backgroundColor: "#10b981",
              color: "white",
              padding: "0.75rem 1.5rem",
              borderRadius: "0.5rem",
              border: "none",
              fontSize: "1rem",
              fontWeight: "500",
              cursor: "pointer",
              transition: "background-color 0.2s",
            }}
            onMouseOver={(e) =>
              (e.currentTarget.style.backgroundColor = "#059669")
            }
            onMouseOut={(e) =>
              (e.currentTarget.style.backgroundColor = "#10b981")
            }
          >
            Intentar nuevamente
          </button>
          {process.env.NODE_ENV === "development" && this.state.error && (
            <details
              style={{
                marginTop: "2rem",
                textAlign: "left",
                maxWidth: "700px",
                width: "100%",
              }}
            >
              <summary
                style={{
                  cursor: "pointer",
                  color: "#ef4444",
                  fontWeight: "500",
                }}
              >
                Error details (development only)
              </summary>
              <pre
                style={{
                  marginTop: "1rem",
                  padding: "1rem",
                  backgroundColor: "#1f2937",
                  color: "#f3f4f6",
                  borderRadius: "0.5rem",
                  fontSize: "0.875rem",
                  overflow: "auto",
                  maxHeight: "300px",
                }}
              >
                {this.state.error.stack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
