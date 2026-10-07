import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { bookingsApi } from "../api/bookings";
import { ApiError } from "../api/client";
import { slotsApi } from "../api/slots";
import { useAuth } from "../hooks/useAuth";
import { bookingKeys, slotKeys, useSlots } from "../hooks/useBookings";
import { useCountdown, type Deadline } from "../hooks/useCountdown";
import { errorMessage } from "../lib/errors";
import { dayKey, formatCountdown, formatDateTime, formatDay, formatTime } from "../lib/time";
import type { Booking, Slot } from "../types/api";
import { ErrorState, Spinner } from "./States";

interface ActiveHold {
  slotStart: string;
  /** Local receive time + the server's expires_in. */
  deadline: Deadline;
}

function groupByDay(slots: Slot[]): [string, Slot[]][] {
  const groups = new Map<string, Slot[]>();
  for (const slot of slots) {
    const key = dayKey(slot.slot_start);
    groups.set(key, [...(groups.get(key) ?? []), slot]);
  }
  return [...groups.entries()];
}

function holdErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "slot_held") return "Someone else is booking that slot right now. Try another time.";
    if (error.code === "slot_booked") return "That slot was just booked. Please pick another.";
  }
  return errorMessage(error);
}

export function SlotPicker({ listingId, acceptingVisits }: { listingId: number; acceptingVisits: boolean }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const slots = useSlots(listingId);

  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [hold, setHold] = useState<ActiveHold | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [booked, setBooked] = useState<Booking | null>(null);

  const remaining = useCountdown(hold?.deadline ?? null);
  const expired = hold !== null && remaining === 0;

  const days = useMemo(() => groupByDay(slots.data ?? []), [slots.data]);
  const firstOpenDay = days.find(([, daySlots]) => daySlots.some((s) => s.status === "available"))?.[0];
  const activeDay = selectedDay ?? firstOpenDay ?? days[0]?.[0] ?? null;
  const daySlots = days.find(([key]) => key === activeDay)?.[1] ?? [];

  const refreshSlots = () => queryClient.invalidateQueries({ queryKey: slotKeys.forListing(listingId) });

  // Release the hold if the buyer leaves, so the slot isn't blocked for the full 5 minutes:
  // on in-app navigation (unmount) and on tab close/reload (pagehide, with a keepalive request
  // the browser finishes even as the page goes away).
  const holdRef = useRef<ActiveHold | null>(null);
  useEffect(() => {
    holdRef.current = booked ? null : hold;
  }, [hold, booked]);
  useEffect(() => {
    const release = () => {
      const current = holdRef.current;
      holdRef.current = null;
      if (current) void slotsApi.release(listingId, current.slotStart, true).catch(() => {});
    };
    window.addEventListener("pagehide", release);
    return () => {
      window.removeEventListener("pagehide", release);
      release();
    };
  }, [listingId]);

  const holdMutation = useMutation({
    mutationFn: async (slotStart: string) => {
      if (hold && hold.slotStart !== slotStart) {
        await slotsApi.release(listingId, hold.slotStart).catch(() => {});
      }
      return slotsApi.hold(listingId, slotStart);
    },
    onMutate: () => setError(null),
    onSuccess: (result) => {
      const startedAt = Date.now();
      setHold({
        slotStart: result.slot_start,
        deadline: { startedAt, endsAt: startedAt + result.expires_in * 1000 },
      });
      void refreshSlots();
    },
    onError: (err) => {
      setHold(null);
      setError(holdErrorMessage(err));
      void refreshSlots();
    },
  });

  const bookMutation = useMutation({
    mutationFn: () => {
      if (!hold) throw new Error("No slot held");
      return bookingsApi.create({ listing_id: listingId, slot_start: hold.slotStart, note: note.trim() || null });
    },
    onMutate: () => setError(null),
    onSuccess: (booking) => {
      setBooked(booking);
      setHold(null);
      void refreshSlots();
      void queryClient.invalidateQueries({ queryKey: bookingKeys.mine });
    },
    onError: (err) => {
      if (err instanceof ApiError && err.code === "hold_required") {
        setHold(null);
        setError("Your hold expired before you confirmed. Please pick the slot again.");
      } else {
        setError(holdErrorMessage(err));
      }
      void refreshSlots();
    },
  });

  const releaseHold = () => {
    if (hold) void slotsApi.release(listingId, hold.slotStart).catch(() => {}).finally(refreshSlots);
    setHold(null);
    setError(null);
  };

  const choose = (slot: Slot) => {
    if (!user) {
      navigate(`/login?next=${encodeURIComponent(location.pathname)}`);
      return;
    }
    holdMutation.mutate(slot.slot_start);
  };

  if (!acceptingVisits) {
    return <p className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-600">This home isn't taking visits right now.</p>;
  }

  if (booked) {
    return (
      <div role="status" className="mt-4 space-y-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4">
        <p className="font-semibold text-emerald-900">Visit requested!</p>
        <p className="text-sm text-emerald-800">
          {formatDateTime(booked.slot_start)}. The agent will confirm shortly, and we've emailed you the details.
        </p>
        <Link to="/my-bookings" className="btn-primary w-full">
          View my bookings
        </Link>
      </div>
    );
  }

  if (slots.isPending) {
    return (
      <div className="mt-4 flex justify-center py-6">
        <Spinner />
      </div>
    );
  }
  if (slots.isError) {
    return (
      <div className="mt-4">
        <ErrorState error={slots.error} onRetry={() => void slots.refetch()} />
      </div>
    );
  }
  if (days.length === 0) {
    return <p className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-600">No visit slots open yet. Check back soon.</p>;
  }

  const isAgent = user?.role === "agent";

  return (
    <div className="mt-4 space-y-4">
      {isAgent && (
        <p className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600">You're signed in as an agent, so booking is disabled.</p>
      )}

      <div role="tablist" aria-label="Visit day" className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
        {days.map(([key, list]) => {
          const open = list.filter((s) => s.status === "available").length;
          const selected = key === activeDay;
          return (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={selected}
              onClick={() => setSelectedDay(key)}
              className={`flex shrink-0 flex-col items-center rounded-lg border px-3 py-2 text-xs transition ${
                selected ? "border-brand-600 bg-brand-50 text-brand-800" : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              <span className="font-semibold">{list[0] ? formatDay(list[0].slot_start) : key}</span>
              <span className="text-slate-500">{open ? `${open} open` : "Full"}</span>
            </button>
          );
        })}
      </div>

      <div role="tabpanel" aria-label="Times" className="grid grid-cols-2 gap-2">
        {daySlots.map((slot) => {
          const mine = hold?.slotStart === slot.slot_start && !expired;
          const taken = !mine && slot.status !== "available";
          const label = mine ? "Your hold" : slot.status === "available" ? "Available" : slot.status === "held" ? "On hold" : "Booked";
          return (
            <button
              key={slot.id}
              type="button"
              disabled={taken || isAgent || holdMutation.isPending}
              aria-pressed={mine}
              aria-label={`${formatTime(slot.slot_start)}, ${label.toLowerCase()}`}
              onClick={() => choose(slot)}
              className={`rounded-lg border px-3 py-2 text-left text-sm transition disabled:cursor-not-allowed ${
                mine
                  ? "border-brand-600 bg-brand-600 text-white"
                  : taken
                    ? "border-slate-200 bg-slate-100 text-slate-400 line-through"
                    : "border-slate-300 bg-white text-slate-800 hover:border-brand-500 hover:bg-brand-50"
              }`}
            >
              <span className="block font-semibold">{formatTime(slot.slot_start)}</span>
              <span className={`text-xs ${mine ? "text-brand-100" : ""}`}>{label}</span>
            </button>
          );
        })}
      </div>

      {error && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {hold && (
        <div className="space-y-3 rounded-lg border border-brand-200 bg-brand-50 p-4">
          {expired ? (
            <>
              <p className="text-sm font-semibold text-slate-900">Your hold expired</p>
              <p className="text-sm text-slate-600">The slot has been released. Pick a time again to continue.</p>
              <button type="button" className="btn-secondary w-full" onClick={releaseHold}>
                Choose again
              </button>
            </>
          ) : (
            <>
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900">{formatDateTime(hold.slotStart)}</p>
                  <p className="text-xs text-slate-600">Held for you while you confirm</p>
                </div>
                <span
                  role="timer"
                  aria-label={`${formatCountdown(remaining)} left on your hold`}
                  className={`rounded-md px-2 py-1 font-mono text-lg font-bold tabular-nums ${
                    remaining <= 60 ? "bg-red-100 text-red-700" : "bg-white text-brand-800"
                  }`}
                >
                  {formatCountdown(remaining)}
                </span>
              </div>
              <div>
                <label htmlFor="visit-note" className="label">
                  Note for the agent <span className="font-normal text-slate-400">(optional)</span>
                </label>
                <textarea
                  id="visit-note"
                  rows={2}
                  maxLength={500}
                  className="input"
                  placeholder="e.g. Coming with family, prefer to see the terrace"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </div>
              <div className="flex gap-2">
                <button type="button" className="btn-secondary flex-1" onClick={releaseHold} disabled={bookMutation.isPending}>
                  Cancel
                </button>
                <button type="button" className="btn-primary flex-[2]" onClick={() => bookMutation.mutate()} disabled={bookMutation.isPending}>
                  {bookMutation.isPending && <Spinner className="h-4 w-4 border-white/40 border-t-white" />} Confirm visit
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {!user && <p className="text-xs text-slate-500">You'll be asked to log in when you pick a time.</p>}
    </div>
  );
}
