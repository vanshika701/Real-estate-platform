/** Only follow same-site relative paths after login, never an attacker-supplied URL. */
export function safeNext(next: string | null): string | null {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : null;
}
