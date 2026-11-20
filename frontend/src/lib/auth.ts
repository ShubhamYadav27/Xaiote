/**
 * Xaiote Authentication Utilities
 *
 * Centralized auth layer that manages JWT access/refresh tokens.
 * Tokens are stored in localStorage and attached to API requests
 * via the fetchApi layer.
 *
 * Backend contract:
 *   POST /api/auth/login     → { data: { access_token, refresh_token } }
 *   POST /api/auth/register  → { data: { message } }
 *   POST /api/auth/refresh   → { data: { access_token, refresh_token } }
 *   POST /api/auth/logout    → { data: { message } }
 *   GET  /api/auth/me         → { data: { email, full_name, company_id } }
 */

const API_BASE = (() => {
  const configuredUrl = process.env.NEXT_PUBLIC_API_URL;
  if (process.env.NODE_ENV === 'production') {
    if (configuredUrl && configuredUrl.includes('localhost')) {
      throw new Error("PRODUCTION CONFIGURATION ERROR: NEXT_PUBLIC_API_URL cannot point to localhost in production.");
    }
    return configuredUrl || 'https://api.xaiote.com/api/v1';
  }
  return configuredUrl || 'http://localhost:8000/api/v1';
})();
const AUTH_API_BASE = API_BASE.replace(/\/api\/v1$/, '/api/auth');

// ────────────────────────────────────────────
// Token storage
// ────────────────────────────────────────────

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('refresh_token');
}

function setTokens(accessToken: string, refreshToken: string) {
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
  // Set cookie signal for middleware route protection
  document.cookie = 'xaiote_auth=1; path=/; max-age=604800; SameSite=Lax';
}

export function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  // Clear cookie signal
  document.cookie = 'xaiote_auth=; path=/; max-age=0';
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

// ────────────────────────────────────────────
// Auth API calls
// ────────────────────────────────────────────

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name: string;
  company_name: string;
  industry?: string;
  revenue_range?: string;
}

export interface AuthUser {
  email: string;
  full_name: string;
  company_id: string;
}

export interface AuthError {
  code: string;
  message: string;
}

async function authFetch(endpoint: string, options: RequestInit = {}): Promise<Record<string, unknown>> {
  let response; 
  try { 
    response = await fetch(`${AUTH_API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
  } catch (err: any) {
    throw new Error(`Network Error: Cannot connect to API (${AUTH_API_BASE}). Ensure backend is running and CORS allows this origin.`);
  }

  const json = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMessage =
      json?.detail || json?.error?.message || `Request failed with status ${response.status}`;
    throw new Error(errorMessage);
  }

  // Backend returns { error: {...} } with 200 for some auth routes (legacy).
  // After our backend fix these will be proper HTTP errors, but handle both.
  if (json.error) {
    throw new Error(json.error.message || 'Authentication error');
  }

  return json;
}

export async function login(credentials: LoginCredentials): Promise<void> {
  const json = await authFetch('/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });

  const data = json.data as { access_token: string; refresh_token: string };
  if (!data?.access_token || !data?.refresh_token) {
    throw new Error('Invalid login response');
  }

  setTokens(data.access_token, data.refresh_token);
}

export async function register(data: RegisterData): Promise<void> {
  await authFetch('/register', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken();
  if (refreshToken) {
    try {
      await authFetch('/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch {
      // Server-side logout failure is non-critical; clear client tokens regardless.
    }
  }
  clearTokens();
}

export async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const json = await authFetch('/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    const data = json.data as { access_token: string; refresh_token: string };
    if (!data?.access_token || !data?.refresh_token) return false;

    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

export async function getCurrentUser(): Promise<AuthUser | null> {
  const token = getAccessToken();
  if (!token) return null;

  try {
    const response = await fetch(`${AUTH_API_BASE}/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
      if (response.status === 401) {
        const refreshed = await refreshAccessToken();
        if (refreshed) return getCurrentUser();
        clearTokens();
      }
      return null;
    }

    const json = await response.json();
    return (json.data as AuthUser) || null;
  } catch {
    return null;
  }
}
