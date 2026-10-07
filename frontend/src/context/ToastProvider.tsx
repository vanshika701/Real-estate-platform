import { useCallback, useMemo, useRef, useState, type ReactNode } from "react";

import { ToastContext, type Toast, type ToastContextValue } from "./toastContext";

const DISMISS_AFTER_MS = 6000;

const TONE_STYLES: Record<Toast["tone"], string> = {
  info: "border-brand-200 bg-white",
  success: "border-emerald-200 bg-emerald-50",
  error: "border-red-200 bg-red-50",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const notify = useCallback<ToastContextValue["notify"]>(
    ({ tone = "info", ...toast }) => {
      const id = nextId.current++;
      setToasts((current) => [...current.slice(-3), { id, tone, ...toast }]);
      window.setTimeout(() => dismiss(id), DISMISS_AFTER_MS);
    },
    [dismiss],
  );

  const value = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* Polite live region: screen readers announce toasts without interrupting. */}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="pointer-events-none fixed inset-x-4 bottom-4 z-[2000] flex flex-col items-end gap-2 sm:left-auto sm:w-96"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className={`pointer-events-auto w-full rounded-xl border p-4 shadow-lg ${TONE_STYLES[toast.tone]}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-900">{toast.title}</p>
                {toast.description && <p className="mt-0.5 text-sm text-slate-600">{toast.description}</p>}
              </div>
              <button
                type="button"
                aria-label="Dismiss notification"
                onClick={() => dismiss(toast.id)}
                className="rounded p-1 text-slate-400 hover:bg-black/5 hover:text-slate-700"
              >
                ×
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
