import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { Spinner } from "../components/States";
import { homeFor, useAuth } from "../hooks/useAuth";
import { errorMessage } from "../lib/errors";
import { safeNext } from "../lib/navigation";
import { signupSchema, type SignupValues } from "./authSchemas";

function FieldError({ id, message }: { id: string; message: string | undefined }) {
  return message ? (
    <p id={id} className="field-error">
      {message}
    </p>
  ) : null;
}

export function SignupPage() {
  const { user, signup } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeNext(params.get("next"));
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<SignupValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: { role: "buyer" },
  });

  if (user) return <Navigate to={next ?? homeFor(user.role)} replace />;

  const onSubmit = async (values: SignupValues) => {
    setServerError(null);
    try {
      const created = await signup({ ...values, phone: values.phone || null });
      navigate(next ?? homeFor(created.role), { replace: true });
    } catch (error) {
      if (error instanceof ApiError && error.code === "email_taken") {
        setError("email", { message: "An account with this email already exists" });
      } else {
        setServerError(errorMessage(error));
      }
    }
  };

  const fieldProps = (name: keyof SignupValues) => ({
    "aria-invalid": errors[name] ? true : undefined,
    "aria-describedby": errors[name] ? `signup-${name}-error` : undefined,
  });

  return (
    <div className="mx-auto flex max-w-md flex-col px-4 py-12">
      <h1 className="text-2xl font-bold tracking-tight">Create your account</h1>
      <p className="mt-1 text-slate-600">Book site visits, or list properties as an agent.</p>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-6 space-y-4" aria-label="Sign up">
        {serverError && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {serverError}
          </p>
        )}

        <fieldset>
          <legend className="label">I want to</legend>
          <div className="grid grid-cols-2 gap-3">
            {(
              [
                ["buyer", "Buy a home", "Browse and book visits"],
                ["agent", "List properties", "Manage visit requests"],
              ] as const
            ).map(([value, title, hint]) => (
              <label
                key={value}
                className="flex cursor-pointer flex-col rounded-lg border border-slate-300 bg-white p-3 has-[:checked]:border-brand-600 has-[:checked]:bg-brand-50 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand-200"
              >
                <input type="radio" value={value} className="sr-only" {...register("role")} />
                <span className="text-sm font-semibold">{title}</span>
                <span className="text-xs text-slate-500">{hint}</span>
              </label>
            ))}
          </div>
          <FieldError id="signup-role-error" message={errors.role?.message} />
        </fieldset>

        <div>
          <label htmlFor="signup-full_name" className="label">
            Full name
          </label>
          <input id="signup-full_name" autoComplete="name" className="input" {...fieldProps("full_name")} {...register("full_name")} />
          <FieldError id="signup-full_name-error" message={errors.full_name?.message} />
        </div>
        <div>
          <label htmlFor="signup-email" className="label">
            Email
          </label>
          <input id="signup-email" type="email" autoComplete="email" className="input" {...fieldProps("email")} {...register("email")} />
          <FieldError id="signup-email-error" message={errors.email?.message} />
        </div>
        <div>
          <label htmlFor="signup-phone" className="label">
            Phone <span className="font-normal text-slate-400">(optional)</span>
          </label>
          <input id="signup-phone" type="tel" autoComplete="tel" placeholder="+919876543210" className="input" {...fieldProps("phone")} {...register("phone")} />
          <FieldError id="signup-phone-error" message={errors.phone?.message} />
        </div>
        <div>
          <label htmlFor="signup-password" className="label">
            Password
          </label>
          <input
            id="signup-password"
            type="password"
            autoComplete="new-password"
            className="input"
            {...fieldProps("password")}
            {...register("password")}
          />
          {errors.password ? (
            <FieldError id="signup-password-error" message={errors.password?.message} />
          ) : (
            <p className="mt-1 text-xs text-slate-500">At least 8 characters, with a letter and a number.</p>
          )}
        </div>

        <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
          {isSubmitting && <Spinner className="h-4 w-4 border-white/40 border-t-white" />} Create account
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-600">
        Already have an account?{" "}
        <Link to={next ? `/login?next=${encodeURIComponent(next)}` : "/login"} className="font-semibold text-brand-700 hover:underline">
          Log in
        </Link>
      </p>
    </div>
  );
}
