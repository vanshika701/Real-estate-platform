import type { Tokens } from "../types/api";

const ACCESS_KEY = "propvisit.access_token";
const REFRESH_KEY = "propvisit.refresh_token";

/**
 * Tokens live in localStorage so a page reload keeps the user signed in.
 *
 * Trade-off: anything in localStorage is readable by injected scripts (XSS). The stronger
 * option is an httpOnly refresh cookie, which needs CSRF protection on the backend; for this
 * project the short 15-minute access token and single-use refresh tokens limit the damage.
 */
function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null; // storage disabled (private mode, blocked cookies)
  }
}

function write(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    // Without storage the session simply won't survive a reload.
  }
}

type Listener = () => void;
const listeners = new Set<Listener>();

export const tokenStore = {
  getAccessToken: (): string | null => read(ACCESS_KEY),
  getRefreshToken: (): string | null => read(REFRESH_KEY),

  set(tokens: Pick<Tokens, "access_token" | "refresh_token">): void {
    write(ACCESS_KEY, tokens.access_token);
    write(REFRESH_KEY, tokens.refresh_token);
  },

  clear(): void {
    write(ACCESS_KEY, null);
    write(REFRESH_KEY, null);
    listeners.forEach((listener) => listener());
  },

  /** Called when the session ends unexpectedly (e.g. the refresh token was rejected). */
  onCleared(listener: Listener): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};
