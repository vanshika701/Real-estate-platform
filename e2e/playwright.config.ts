import { defineConfig, devices } from "@playwright/test";

const CI = Boolean(process.env.CI);

/**
 * Runs against the full Docker Compose stack (nginx → frontend + API + worker + Postgres +
 * Redis), so these tests exercise the same paths a real user's browser does.
 */
export default defineConfig({
  testDir: "./tests",
  // The journeys share data (the buyer books, then the agent accepts), so run them in order.
  fullyParallel: false,
  workers: 1,
  retries: CI ? 1 : 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: CI ? [["github"], ["html", { open: "never" }]] : [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } } }],
});
