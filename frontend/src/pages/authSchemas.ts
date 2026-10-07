import { z } from "zod";

// Mirrors the backend's rules so most mistakes are caught before a round trip;
// the server still validates everything.
const email = z.string().trim().min(1, "Enter your email").email("Enter a valid email");

export const loginSchema = z.object({
  email,
  password: z.string().min(1, "Enter your password"),
});

export const signupSchema = z.object({
  full_name: z.string().trim().min(1, "Enter your name").max(120, "Name is too long"),
  email,
  password: z
    .string()
    .min(8, "Use at least 8 characters")
    .max(72, "Use at most 72 characters")
    .regex(/[A-Za-z]/, "Include at least one letter")
    .regex(/\d/, "Include at least one number"),
  role: z.enum(["buyer", "agent"], { message: "Choose how you'll use PropVisit" }),
  phone: z
    .string()
    .trim()
    .regex(/^(\+?\d{10,15})?$/, "Enter 10–15 digits, optionally starting with +")
    .optional(),
});

export type LoginValues = z.infer<typeof loginSchema>;
export type SignupValues = z.infer<typeof signupSchema>;
