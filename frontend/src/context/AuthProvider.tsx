import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { authApi } from "../api/auth";
import { tokenStore } from "../api/tokenStore";
import type { AuthResponse, LoginRequest, SignupRequest, User } from "../types/api";
import { AuthContext } from "./authContext";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(() => tokenStore.getAccessToken() !== null);

  // Restore the session on load. /auth/me refreshes the access token if it has expired.
  useEffect(() => {
    if (!tokenStore.getAccessToken()) return;
    let cancelled = false;
    authApi
      .me()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch(() => {
        if (!cancelled) tokenStore.clear();
      })
      .finally(() => {
        if (!cancelled) setInitializing(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // If a refresh fails mid-session, the API client clears the tokens; reflect that here.
  useEffect(() => tokenStore.onCleared(() => setUser(null)), []);

  const startSession = useCallback((response: AuthResponse) => {
    tokenStore.set(response);
    setUser(response.user);
    return response.user;
  }, []);

  const login = useCallback(
    async (data: LoginRequest) => startSession(await authApi.login(data)),
    [startSession],
  );

  const signup = useCallback(
    async (data: SignupRequest) => startSession(await authApi.signup(data)),
    [startSession],
  );

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
    queryClient.clear(); // drop any cached private data (bookings, dashboards)
  }, [queryClient]);

  const value = useMemo(
    () => ({ user, initializing, login, signup, logout }),
    [user, initializing, login, signup, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
