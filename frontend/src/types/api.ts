/** Shape of every error response from the backend. */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
  };
}

export type DependencyStatus = "ok" | "error";

export interface HealthResponse {
  status: "ok" | "degraded";
  checks: Record<string, DependencyStatus>;
}
