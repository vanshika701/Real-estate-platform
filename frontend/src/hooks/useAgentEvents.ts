import { useEffect, useRef, useState } from "react";

import { authApi } from "../api/auth";
import { API_ORIGIN } from "../api/client";
import { tokenStore } from "../api/tokenStore";
import type { AgentEvent } from "../types/api";

export type ConnectionState = "connecting" | "live" | "reconnecting" | "offline";

const CLOSE_UNAUTHORIZED = 4401;
const CLOSE_FORBIDDEN = 4403;
const MAX_BACKOFF_MS = 30_000;

function socketUrl(token: string): string {
  const base = API_ORIGIN
    ? API_ORIGIN.replace(/^http/, "ws")
    : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;
  return `${base}/api/v1/ws/agent?token=${encodeURIComponent(token)}`;
}

/**
 * Live booking events for the signed-in agent.
 *
 * Reconnects with exponential backoff. If the server rejects the token (it expires after
 * 15 minutes), it refreshes the session once and reconnects. `onReconnect` lets the caller
 * refetch, since events sent while the socket was down are not replayed.
 */
export function useAgentEvents(
  onEvent: (event: AgentEvent) => void,
  onReconnect?: () => void,
): ConnectionState {
  const [state, setState] = useState<ConnectionState>("connecting");
  // Latest callbacks in refs, so new handler identities don't tear down the socket.
  const onEventRef = useRef(onEvent);
  const onReconnectRef = useRef(onReconnect);
  useEffect(() => {
    onEventRef.current = onEvent;
    onReconnectRef.current = onReconnect;
  });

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: number | undefined;
    let attempts = 0;
    let stopped = false;

    const connect = () => {
      const token = tokenStore.getAccessToken();
      if (!token || stopped) {
        setState("offline");
        return;
      }
      socket = new WebSocket(socketUrl(token));

      socket.onopen = () => {
        if (attempts > 0) onReconnectRef.current?.();
        attempts = 0;
        setState("live");
      };

      socket.onmessage = (message: MessageEvent<string>) => {
        try {
          const event = JSON.parse(message.data) as AgentEvent;
          if (event.type !== "ping") onEventRef.current(event);
        } catch {
          // Ignore malformed frames rather than crashing the dashboard.
        }
      };

      socket.onclose = (close) => {
        if (stopped) return;
        if (close.code === CLOSE_FORBIDDEN) {
          setState("offline");
          return;
        }
        attempts += 1;
        setState("reconnecting");
        const delay = Math.min(1000 * 2 ** (attempts - 1), MAX_BACKOFF_MS);
        retryTimer = window.setTimeout(() => {
          if (close.code === CLOSE_UNAUTHORIZED) {
            // Likely an expired access token: /auth/me refreshes it as a side effect.
            authApi.me().then(connect, () => setState("offline"));
          } else {
            connect();
          }
        }, delay);
      };
    };

    connect();
    return () => {
      stopped = true;
      window.clearTimeout(retryTimer);
      socket?.close();
    };
  }, []);

  return state;
}
