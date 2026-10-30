/**
 * Ejemplo: Login con Telemetría
 *
 * Muestra cómo instrumentar eventos de autenticación:
 * - login_attempt_failed (con failure_reason)
 * - login_attempt_success
 * - session_expired
 *
 * IMPORTANTE: NUNCA loguear email o password en claro.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { trackLoginFailed, trackLoginSuccess } from "@/lib/telemetry-hooks";

export function LoginFormWithTelemetry() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({
          username: email,
          password: password,
        }),
      });

      if (!response.ok) {
        const data = await response.json();

        // ============================================================
        // TELEMETRY: Login Failed
        // ============================================================

        // Determinar failure_reason según response
        let failureReason: "invalid_credentials" | "account_locked" | "network_error";

        if (response.status === 401) {
          failureReason = "invalid_credentials";
        } else if (response.status === 403) {
          failureReason = "account_locked";
        } else {
          failureReason = "network_error";
        }

        // Hash del email (SHA256) para detección de ataques
        // En producción, hashear en servidor para evitar exponer email en JS
        const emailHash = await hashEmail(email);

        trackLoginFailed(failureReason, emailHash);

        // ============================================================

        setError(data.detail || "Credenciales inválidas");
        return;
      }

      const data = await response.json();
      const token = data.access_token;

      // Guardar token
      localStorage.setItem("token", token);

      // ============================================================
      // TELEMETRY: Login Success
      // ============================================================

      // Extraer userId del token JWT
      const payload = JSON.parse(atob(token.split(".")[1]));
      const userId = payload.sub || payload.user_id;

      trackLoginSuccess(userId);

      // ============================================================

      // Redirigir a dashboard
      router.push("/");

    } catch (error) {
      console.error("Login error:", error);

      // ============================================================
      // TELEMETRY: Network Error
      // ============================================================

      trackLoginFailed("network_error");

      // ============================================================

      setError("Error de conexión. Por favor, intenta nuevamente.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-700">
          Email
        </label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
        />
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-700">
          Password
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
        />
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={isLoading}
        className="w-full rounded-md bg-green-600 px-4 py-2 text-white hover:bg-green-700 disabled:opacity-50"
      >
        {isLoading ? "Iniciando sesión..." : "Iniciar sesión"}
      </button>
    </form>
  );
}

/**
 * Hash email con SHA256 (Web Crypto API).
 * En producción, hacer esto en el servidor para evitar exponer email en JS.
 */
async function hashEmail(email: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(email.toLowerCase().trim());
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
  return hashHex;
}
