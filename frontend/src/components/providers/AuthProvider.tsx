'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getCurrentUser, logout as authLogout, type AuthUser } from '@/lib/auth';

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  error: string | null;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  error: null,
  logout: async () => {},
  refreshUser: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshUser = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const u = await getCurrentUser();
      setUser(u);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Failed to load user';
      setError(message);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const logout = useCallback(async () => {
    await authLogout();
    setUser(null);
    window.location.href = '/login';
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, error, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}
