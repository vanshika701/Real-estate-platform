import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { homeFor, useAuth } from "../hooks/useAuth";
import type { UserRole } from "../types/api";
import { PageSpinner } from "./States";

interface Props {
  role: UserRole;
  children: ReactNode;
}

/** Signed-out users go to login (and come back afterwards); the wrong role goes to its own home. */
export function ProtectedRoute({ role, children }: Props) {
  const { user, initializing } = useAuth();
  const location = useLocation();

  if (initializing) return <PageSpinner />;
  if (!user) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  if (user.role !== role) return <Navigate to={homeFor(user.role)} replace />;
  return <>{children}</>;
}
