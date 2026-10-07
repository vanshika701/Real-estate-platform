import type { ApiErrorBody, HealthResponse } from "../types/api";

// Empty by default: requests go to same-origin /api, proxied by Vite (dev) or nginx (Docker).
// Set VITE_API_URL only when the frontend and backend live on different hosts (e.g. Vercel + Render).
const API_BASE = `${import.meta.env.VITE_API_URL ?? ""}/api/v1`;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== "object" || value === null || !("error" in value)) return false;
  const { error } = value as { error: unknown };
  return typeof error === "object" && error !== null && "code" in error && "message" in error;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    if (isApiErrorBody(body)) {
      throw new ApiError(response.status, body.error.code, body.error.message);
    }
    throw new ApiError(response.status, "unknown_error", response.statusText);
  }
  return body as T;
}

export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}
