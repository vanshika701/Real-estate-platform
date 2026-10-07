import { createContext } from "react";

export type ToastTone = "info" | "success" | "error";

export interface Toast {
  id: number;
  title: string;
  description?: string;
  tone: ToastTone;
}

export interface ToastContextValue {
  notify: (toast: Omit<Toast, "id" | "tone"> & { tone?: ToastTone }) => void;
}

export const ToastContext = createContext<ToastContextValue | null>(null);
