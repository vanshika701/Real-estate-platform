import { useEffect, useState } from "react";

export interface Deadline {
  /** Local epoch ms when the countdown starts (captured when the hold response arrived). */
  startedAt: number;
  /** Local epoch ms when it reaches zero. */
  endsAt: number;
}

/**
 * Seconds remaining until `deadline.endsAt`, ticking once a second.
 *
 * Callers build the deadline from the server's `expires_in` plus the local receive time, not
 * from `expires_at`, so a wrong clock on the user's device can't shorten or stretch it.
 * `startedAt` matters because the ticking clock only runs while a deadline exists: without it,
 * a new countdown would briefly measure from whenever the clock last ticked.
 */
export function useCountdown(deadline: Deadline | null): number {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (deadline === null) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [deadline]);

  if (deadline === null) return 0;
  const effectiveNow = Math.max(now, deadline.startedAt);
  return Math.max(0, Math.ceil((deadline.endsAt - effectiveNow) / 1000));
}
