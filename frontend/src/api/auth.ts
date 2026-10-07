import type { AuthResponse, LoginRequest, SignupRequest, User } from "../types/api";
import { apiRequest } from "./client";

export const authApi = {
  login: (data: LoginRequest) =>
    apiRequest<AuthResponse>("/auth/login", { method: "POST", body: data }),
  signup: (data: SignupRequest) =>
    apiRequest<AuthResponse>("/auth/signup", { method: "POST", body: data }),
  me: () => apiRequest<User>("/auth/me", { auth: true }),
};
