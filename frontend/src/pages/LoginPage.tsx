import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { Spinner } from "../components/States";
import { homeFor, useAuth } from "../hooks/useAuth";
import { DEMO_ACCOUNTS } from "../lib/constants";
import { errorMessage } from "../lib/errors";
import { safeNext } from "../lib/navigation";
import type { User } from "../types/api";
import { loginSchema, type LoginValues } from "./authSchemas";

function loginErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.code === "too_many_attempts" && error.retryAfter) {
    const minutes = Math.ceil(error.retryAfter / 60);
    return `Too many failed attempts. Try again in ${minutes} minute${minutes === 1 ? "" : "s"}.`;
  }
  return errorMessage(error);
}

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const [serverError, setServerError] = useState<string | null>(null);
  const [demoPending, setDemoPending] = useState<"buyer" | "agent" | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });

  if (user) return <Navigate to={next ?? homeFor(user.role)} replace />;

  const finish = (signedIn: User) => navigate(next ?? homeFor(signedIn.role), { replace: true });

  const onSubmit = async (values: LoginValues) => {
    setServerError(null);
    try {
      finish(await login(values));
    } catch (error) {
      setServerError(loginErrorMessage(error));
    }
  };

  const tryDemo = async (role: "buyer" | "agent") => {
    setServerError(null);
    setDemoPending(role);
    try {
      finish(await login(DEMO_ACCOUNTS[role]));
    } catch (error) {
      setServerError(loginErrorMessage(error));
    } finally {
      setDemoPending(null);
    }
  };

  const busy = isSubmitting || demoPending !== null;

  return (
    <div className="mx-auto flex max-w-md flex-col px-4 py-12">
      <h1 className="text-2xl font-bold tracking-tight">Welcome back</h1>
      <p className="mt-1 text-slate-600">Log in to book visits or manage your listings.</p>

      <div className="mt-6 grid grid-cols-2 gap-3">
        <button type="button" className="btn-secondary" disabled={busy} onClick={() => void tryDemo("buyer")}>
          {demoPending === "buyer" && <Spinner className="h-4 w-4" />} Try as Buyer
        </button>
        <button type="button" className="btn-secondary" disabled={busy} onClick={() => void tryDemo("agent")}>
          {demoPending === "agent" && <Spinner className="h-4 w-4" />} Try as Agent
        </button>
      </div>

      <div className="my-6 flex items-center gap-3 text-xs uppercase tracking-wide text-slate-400">
        <span className="h-px flex-1 bg-slate-200" /> or with email <span className="h-px flex-1 bg-slate-200" />
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4" aria-label="Log in">
        {serverError && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {serverError}
          </p>
        )}
        <div>
          <label htmlFor="login-email" className="label">
            Email
          </label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            className="input"
            aria-invalid={errors.email ? true : undefined}
            aria-describedby={errors.email ? "login-email-error" : undefined}
            {...register("email")}
          />
          {errors.email && (
            <p id="login-email-error" className="field-error">
              {errors.email.message}
            </p>
          )}
        </div>
        <div>
          <label htmlFor="login-password" className="label">
            Password
          </label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            className="input"
            aria-invalid={errors.password ? true : undefined}
            aria-describedby={errors.password ? "login-password-error" : undefined}
            {...register("password")}
          />
          {errors.password && (
            <p id="login-password-error" className="field-error">
              {errors.password.message}
            </p>
          )}
        </div>
        <button type="submit" className="btn-primary w-full" disabled={busy}>
          {isSubmitting && <Spinner className="h-4 w-4 border-white/40 border-t-white" />} Log in
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-600">
        New here?{" "}
        <Link to={next ? `/signup?next=${encodeURIComponent(next)}` : "/signup"} className="font-semibold text-brand-700 hover:underline">
          Create an account
        </Link>
      </p>
    </div>
  );
}
