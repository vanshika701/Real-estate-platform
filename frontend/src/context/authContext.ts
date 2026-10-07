import { createContext } from "react";

import type { LoginRequest, SignupRequest, User } from "../types/api";

export interface AuthContextValue {
  user: User | null;
  /** True while we restore a session from stored tokens on first load. */
  initializing: boolean;
  login: (data: LoginRequest) => Promise<User>;
  signup: (data: SignupRequest) => Promise<User>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
