import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { vi } from "vitest";

import { AuthContext, type AuthContextValue } from "../src/context/authContext";
import { ToastProvider } from "../src/context/ToastProvider";
import type { User } from "../src/types/api";

export const buyer: User = {
  id: 1,
  email: "buyer@demo.com",
  full_name: "Ananya Verma",
  phone: null,
  role: "buyer",
  created_at: "2026-01-01T00:00:00Z",
};

export const agent: User = { ...buyer, id: 2, email: "agent@demo.com", full_name: "Aarav Mehta", role: "agent" };

/** Renders the current URL so tests can assert on navigation and query-string sync. */
function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname + location.search}</output>;
}

interface Options {
  route?: string;
  /** Route pattern for `ui`, e.g. "/listings/:id". */
  path?: string;
  user?: User | null;
  auth?: Partial<AuthContextValue>;
}

export function renderWithProviders(ui: ReactElement, { route = "/", path = "*", user = null, auth }: Options = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity }, mutations: { retry: false } },
  });
  const authValue: AuthContextValue = {
    user,
    initializing: false,
    login: vi.fn(),
    signup: vi.fn(),
    logout: vi.fn(),
    ...auth,
  };

  const result = render(
    <QueryClientProvider client={queryClient}>
      <AuthContext.Provider value={authValue}>
        <ToastProvider>
          <MemoryRouter initialEntries={[route]}>
            <Routes>
              <Route
                path={path}
                element={
                  <>
                    {ui}
                    <LocationProbe />
                  </>
                }
              />
              {path !== "*" && <Route path="*" element={<LocationProbe />} />}
            </Routes>
          </MemoryRouter>
        </ToastProvider>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
  return { ...result, authValue, queryClient };
}

export function currentLocation(container: HTMLElement = document.body): string {
  return container.querySelector('[data-testid="location"]')?.textContent ?? "";
}
