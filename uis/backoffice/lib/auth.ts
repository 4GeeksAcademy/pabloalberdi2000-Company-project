/**
 * Authentication Token Management
 * SSR-safe helpers for localStorage
 */

const TOKEN_KEY = 'brasaland_auth_token';

/**
 * Get JWT token from localStorage
 * Returns null if running on server or token doesn't exist
 */
export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Save JWT token to localStorage
 * No-op if running on server
 */
export function setToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
}

/**
 * Remove JWT token from localStorage
 * No-op if running on server
 */
export function removeToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
}
