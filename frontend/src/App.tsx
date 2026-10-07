import { useEffect, useState } from "react";

import { getHealth } from "./api/client";
import type { HealthResponse } from "./types/api";

type HealthState =
  | { kind: "loading" }
  | { kind: "loaded"; data: HealthResponse }
  | { kind: "error"; message: string };

// Placeholder landing page for Phase 1: proves the frontend can reach the API end to end.
export default function App() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    getHealth()
      .then((data) => setHealth({ kind: "loaded", data }))
      .catch((err: unknown) =>
        setHealth({ kind: "error", message: err instanceof Error ? err.message : "Unknown error" }),
      );
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-slate-50 px-4 text-slate-900">
      <h1 className="text-4xl font-bold tracking-tight">PropVisit</h1>
      <p className="max-w-md text-center text-slate-600">
        Browse property listings and book site visits.
      </p>
      <section
        aria-live="polite"
        className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
      >
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
          API status
        </h2>
        {health.kind === "loading" && <p className="text-slate-500">Checking…</p>}
        {health.kind === "error" && <p className="text-red-600">Unreachable: {health.message}</p>}
        {health.kind === "loaded" && (
          <ul className="space-y-1">
            {Object.entries(health.data.checks).map(([name, status]) => (
              <li key={name} className="flex justify-between">
                <span className="capitalize">{name}</span>
                <span className={status === "ok" ? "text-green-600" : "text-red-600"}>
                  {status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
