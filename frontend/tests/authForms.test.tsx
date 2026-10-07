import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../src/api/client";
import { LoginPage } from "../src/pages/LoginPage";
import { SignupPage } from "../src/pages/SignupPage";
import { agent, buyer, currentLocation, renderWithProviders } from "./utils";

describe("<LoginPage>", () => {
  it("validates before calling the API", async () => {
    const login = vi.fn();
    renderWithProviders(<LoginPage />, { route: "/login", auth: { login } });

    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByText("Enter your email")).toBeInTheDocument();
    expect(screen.getByText("Enter your password")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
    expect(login).not.toHaveBeenCalled();
  });

  it("rejects a malformed email", async () => {
    renderWithProviders(<LoginPage />, { route: "/login" });

    await userEvent.type(screen.getByLabelText("Email"), "riya@");
    await userEvent.type(screen.getByLabelText("Password"), "whatever");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByText("Enter a valid email")).toBeInTheDocument();
  });

  it("logs in and goes to the role's home", async () => {
    const login = vi.fn().mockResolvedValue(agent);
    renderWithProviders(<LoginPage />, { route: "/login", auth: { login } });

    await userEvent.type(screen.getByLabelText("Email"), "agent@demo.com");
    await userEvent.type(screen.getByLabelText("Password"), "Demo@1234");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(login).toHaveBeenCalledWith({ email: "agent@demo.com", password: "Demo@1234" });
    await waitFor(() => expect(currentLocation()).toBe("/agent/dashboard"));
  });

  it("returns to ?next after login, but only for same-site paths", async () => {
    const login = vi.fn().mockResolvedValue(buyer);
    renderWithProviders(<LoginPage />, { route: "/login?next=%2Flistings%2F7", auth: { login } });

    await userEvent.click(screen.getByRole("button", { name: "Try as Buyer" }));

    await waitFor(() => expect(currentLocation()).toBe("/listings/7"));
  });

  it("ignores an off-site ?next", async () => {
    const login = vi.fn().mockResolvedValue(buyer);
    renderWithProviders(<LoginPage />, { route: "/login?next=https%3A%2F%2Fevil.com", auth: { login } });

    await userEvent.click(screen.getByRole("button", { name: "Try as Buyer" }));

    await waitFor(() => expect(currentLocation()).toBe("/listings"));
  });

  it("logs in with the demo accounts in one click", async () => {
    const login = vi.fn().mockResolvedValue(agent);
    renderWithProviders(<LoginPage />, { route: "/login", auth: { login } });

    await userEvent.click(screen.getByRole("button", { name: "Try as Agent" }));

    expect(login).toHaveBeenCalledWith({ email: "agent@demo.com", password: "Demo@1234" });
  });

  it("shows the lockout in minutes when rate limited", async () => {
    const login = vi.fn().mockRejectedValue(new ApiError(429, "too_many_attempts", "Too many", 600));
    renderWithProviders(<LoginPage />, { route: "/login", auth: { login } });

    await userEvent.type(screen.getByLabelText("Email"), "riya@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "Wrong1234");
    await userEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Try again in 10 minutes.");
  });
});

describe("<SignupPage>", () => {
  const fill = async (overrides: Record<string, string> = {}) => {
    const values = { "Full name": "Riya S", Email: "riya@example.com", Password: "Secret123", ...overrides };
    for (const [label, value] of Object.entries(values)) {
      if (value) await userEvent.type(screen.getByLabelText(label), value);
    }
  };

  it.each([
    [{ Password: "short1" }, "Use at least 8 characters"],
    [{ Password: "nodigitshere" }, "Include at least one number"],
    [{ Password: "12345678" }, "Include at least one letter"],
    [{ Email: "not-an-email" }, "Enter a valid email"],
    [{ "Full name": "" }, "Enter your name"],
  ])("rejects %o with %s", async (overrides, message) => {
    const signup = vi.fn();
    renderWithProviders(<SignupPage />, { route: "/signup", auth: { signup } });

    await fill(overrides);
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(signup).not.toHaveBeenCalled();
  });

  it("validates the optional phone only when given", async () => {
    renderWithProviders(<SignupPage />, { route: "/signup" });

    await fill();
    await userEvent.type(screen.getByLabelText(/Phone/), "12ab");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText(/Enter 10–15 digits/)).toBeInTheDocument();
  });

  it("signs up as the chosen role and goes to its home", async () => {
    const signup = vi.fn().mockResolvedValue(agent);
    renderWithProviders(<SignupPage />, { route: "/signup", auth: { signup } });

    await userEvent.click(screen.getByText("List properties"));
    await fill();
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(signup).toHaveBeenCalledWith({
      full_name: "Riya S",
      email: "riya@example.com",
      password: "Secret123",
      role: "agent",
      phone: null,
    });
    await waitFor(() => expect(currentLocation()).toBe("/agent/dashboard"));
  });

  it("puts 'email taken' on the email field", async () => {
    const signup = vi.fn().mockRejectedValue(new ApiError(409, "email_taken", "taken"));
    renderWithProviders(<SignupPage />, { route: "/signup", auth: { signup } });

    await fill();
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("An account with this email already exists")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
  });
});
