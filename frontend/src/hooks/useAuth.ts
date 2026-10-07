import { useContext } from "react";

import { AuthContext, type AuthContextValue } from "../context/authContext";
import type { UserRole } from "../types/api";

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}

/** Where each role lands after signing in. */
export function homeFor(role: UserRole): string {
  return role === "agent" ? "/agent/dashboard" : "/listings";
}
