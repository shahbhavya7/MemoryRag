// Holds the logged-in user's JWT and email in React state / memory only.
// On refresh this resets (no localStorage yet, by design for this phase).

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { api, setAuthToken } from "../api/client";

interface AuthState {
  token: string | null;
  email: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);

  const login = useCallback(async (emailInput: string, password: string) => {
    const { access_token } = await api.login(emailInput, password);
    setAuthToken(access_token); // wire it into the API client for all future calls
    setToken(access_token);
    setEmail(emailInput);
  }, []);

  const register = useCallback(
    async (emailInput: string, password: string) => {
      // Register, then log straight in so the user lands in the app.
      await api.register(emailInput, password);
      await login(emailInput, password);
    },
    [login],
  );

  const logout = useCallback(() => {
    setAuthToken(null);
    setToken(null);
    setEmail(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({ token, email, isAuthenticated: !!token, login, register, logout }),
    [token, email, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
