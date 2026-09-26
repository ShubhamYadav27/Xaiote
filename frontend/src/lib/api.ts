/**
 * Xaiote API Client
 *
 * Centralized fetch wrapper for all backend API calls.
 * Automatically attaches auth tokens and handles 401 refresh.
 *
 * Usage:
 *   const data = await fetchApi('/customers?limit=10');
 *   await fetchApi('/customers', { method: 'POST', body: JSON.stringify({...}) });
 *
 * For file uploads (FormData), use fetchApiRaw() which skips Content-Type.
 */

import { getAccessToken, refreshAccessToken, clearTokens } from './auth';

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === 'production'
    ? 'https://api.xaiote.com/api/v1'
    : 'http://localhost:8000/api/v1');

/**
 * Main API fetch for JSON endpoints under /api/v1/*.
 * Automatically attaches Bearer token and handles 401 refresh.
 * Returns the `data` field from the standard { data: ... } envelope.
 */
export async function fetchApi(endpoint: string, options: RequestInit = {}): Promise<any> {
  const response = await _doFetch(endpoint, options);
  return response;
}

/**
 * Raw fetch for multipart uploads (FormData).
 * Does NOT set Content-Type (browser sets it with boundary).
 * Returns full parsed JSON.
 */
export async function fetchApiUpload(
  endpoint: string,
  body: FormData,
  method: string = 'POST',
): Promise<any> {
  const token = getAccessToken();
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers,
    body,
  });

  const json = await response.json().catch(() => ({}));

  if (response.status === 401) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return fetchApiUpload(endpoint, body, method);
    }
    clearTokens();
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
    throw new Error('Session expired. Please log in again.');
  }

  if (!response.ok) {
    throw new Error(json?.detail || json?.error?.message || `Request failed (${response.status})`);
  }

  if (json.error) {
    throw new Error(json.error.message || 'An error occurred');
  }

  return json.data !== undefined ? json.data : json;
}

// ────────────────────────────────────────────
// Internal
// ────────────────────────────────────────────

async function _doFetch(endpoint: string, options: RequestInit = {}, isRetry = false): Promise<any> {
  const token = getAccessToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });
  } catch (err: any) {
    throw new Error(`Network Error: Cannot connect to API (${API_BASE_URL}). Ensure backend is running and CORS allows this origin.`);
  }

  const json = await response.json().catch(() => ({}));

  // Handle 401: attempt one token refresh
  if (response.status === 401 && !isRetry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return _doFetch(endpoint, options, true);
    }
    clearTokens();
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
    throw new Error('Session expired. Please log in again.');
  }

  if (!response.ok) {
    throw new Error(json?.detail || json?.error?.message || `Request failed (${response.status})`);
  }

  if (json.error) {
    throw new Error(json.error.message || 'An error occurred');
  }

  return json.data !== undefined ? json.data : json;
}