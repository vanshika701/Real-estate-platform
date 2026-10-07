import type { ApiErrorBody, Tokens } from "../types/api";
import { tokenStore } from "./tokenStore";

// Empty by default: requests go to same-origin /api, proxied by Vite (dev) or nginx (Docker).
// Set VITE_API_URL only when the frontend and backend live on different hosts (e.g. Vercel + Render).
export const API_ORIGIN = import.meta.env.VITE_API_URL ?? "";
const API_BASE = `${API_ORIGIN}/api/v1`;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryAfter: number | null;

  constructor(status: number, code: string, message: string, retryAfter: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.retryAfter = retryAfter;
  }
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== "object" || value === null || !("error" in value)) return false;
  const { error } = value as { error: unknown };
  return typeof error === "object" && error !== null && "code" in error && "message" in error;
}

type Query = Record<string, string | number | undefined | null>;

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  query?: Query;
  body?: unknown;
  /** Send the access token (and refresh it if expired). */
  auth?: boolean;
  /** Let the request finish even if the page is closing (used to release holds). */
  keepalive?: boolean;
}

function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return `${API_BASE}${path}${qs ? `?${qs}` : ""}`;
}

async function send(path: string, options: RequestOptions): Promise<Response> {
  const headers = new Headers();
  let body: BodyInit | undefined;
  if (options.body instanceof FormData) {
    body = options.body; // the browser sets the multipart boundary itself
  } else if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }
  const token = options.auth ? tokenStore.getAccessToken() : null;
  if (token) headers.set("Authorization", `Bearer ${token}`);

  return fetch(buildUrl(path, options.query), {
    method: options.method ?? "GET",
    headers,
    body,
    keepalive: options.keepalive,
  });
}

async function toError(response: Response): Promise<ApiError> {
  const body: unknown = await response.json().catch(() => null);
  const retryAfter = Number(response.headers.get("Retry-After")) || null;
  if (isApiErrorBody(body)) {
    return new ApiError(response.status, body.error.code, body.error.message, retryAfter);
  }
  return new ApiError(response.status, "unknown_error", response.statusText || "Request failed");
}

// One refresh at a time: if several requests hit an expired token together, they all wait
// for the same refresh instead of each spending (and invalidating) the single-use token.
let refreshInFlight: Promise<boolean> | null = null;

function refreshTokens(): Promise<boolean> {
  refreshInFlight ??= (async () => {
    const refreshToken = tokenStore.getRefreshToken();
    if (!refreshToken) return false;
    const response = await send("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
    });
    if (!response.ok) {
      tokenStore.clear();
      return false;
    }
    tokenStore.set((await response.json()) as Tokens);
    return true;
  })().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response = await send(path, options);

  if (response.status === 401 && options.auth && tokenStore.getRefreshToken()) {
    const error = await toError(response.clone());
    if (error.code === "token_expired" && (await refreshTokens())) {
      response = await send(path, options);
    }
  }

  if (!response.ok) throw await toError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Image URLs from local storage are relative ("/uploads/..."); make them absolute if needed. */
export function resolveImageUrl(url: string): string {
  return url.startsWith("/") ? `${API_ORIGIN}${url}` : url;
}
