import { useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, PageSpinner, Spinner } from "../components/States";
import { StatusBadge } from "../components/StatusBadge";
import { useCancelBooking, useMyBookings } from "../hooks/useBookings";
import { useToast } from "../hooks/useToast";
import { errorMessage } from "../lib/errors";
import { formatDateTime } from "../lib/time";
import type { Booking } from "../types/api";

const CANCELLABLE = new Set(["pending", "accepted"]);

function BookingRow({ booking, upcoming }: { booking: Booking; upcoming: boolean }) {
  const cancel = useCancelBooking();
  const { notify } = useToast();
  const [confirming, setConfirming] = useState(false);
  const canCancel = upcoming && CANCELLABLE.has(booking.status);

  const doCancel = () =>
    cancel.mutate(booking.id, {
      onSuccess: () => notify({ title: "Visit cancelled", tone: "success" }),
      onError: (error) => notify({ title: "Couldn't cancel", description: errorMessage(error), tone: "error" }),
      onSettled: () => setConfirming(false),
    });

  return (
    <li className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={booking.status} />
          <span className="text-sm font-semibold text-slate-900">{formatDateTime(booking.slot_start)}</span>
        </div>
        <Link to={`/listings/${booking.listing.id}`} className="block truncate font-medium text-brand-700 hover:underline">
          {booking.listing.title}
        </Link>
        <p className="text-sm text-slate-500">{booking.listing.address}</p>
        {booking.note && <p className="text-sm text-slate-600 italic">“{booking.note}”</p>}
      </div>

      {canCancel && (
        <div className="flex shrink-0 gap-2">
          {confirming ? (
            <>
              <button type="button" className="btn-secondary py-2" onClick={() => setConfirming(false)} disabled={cancel.isPending}>
                Keep
              </button>
              <button
                type="button"
                className="btn-primary bg-red-600 py-2 hover:bg-red-700"
                onClick={doCancel}
                disabled={cancel.isPending}
              >
                {cancel.isPending && <Spinner className="h-4 w-4 border-white/40 border-t-white" />} Yes, cancel
              </button>
            </>
          ) : (
            <button type="button" className="btn-secondary py-2" onClick={() => setConfirming(true)}>
              Cancel visit
            </button>
          )}
        </div>
      )}
    </li>
  );
}

export function MyBookingsPage() {
  const query = useMyBookings();
  // Captured once per visit: good enough to split upcoming from past, and keeps render pure.
  const [now] = useState(() => Date.now());

  if (query.isPending) return <PageSpinner />;

  const bookings = query.data ?? [];
  const upcoming = bookings
    .filter((b) => new Date(b.slot_start).getTime() > now)
    .sort((a, b) => a.slot_start.localeCompare(b.slot_start));
  const past = bookings.filter((b) => new Date(b.slot_start).getTime() <= now);

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <h1 className="text-2xl font-bold tracking-tight">My bookings</h1>
      <p className="text-slate-600">Your site visit requests and their status.</p>

      <div className="mt-6 space-y-8">
        {query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : bookings.length === 0 ? (
          <EmptyState
            title="No visits booked yet"
            description="Find a home you like and pick a visit slot."
            action={
              <Link to="/listings" className="btn-primary">
                Browse homes
              </Link>
            }
          />
        ) : (
          <>
            <section aria-labelledby="upcoming-heading">
              <h2 id="upcoming-heading" className="mb-3 text-lg font-semibold">
                Upcoming ({upcoming.length})
              </h2>
              {upcoming.length === 0 ? (
                <p className="text-sm text-slate-500">Nothing coming up.</p>
              ) : (
                <ul className="space-y-3">
                  {upcoming.map((b) => (
                    <BookingRow key={b.id} booking={b} upcoming />
                  ))}
                </ul>
              )}
            </section>
            {past.length > 0 && (
              <section aria-labelledby="past-heading">
                <h2 id="past-heading" className="mb-3 text-lg font-semibold text-slate-700">
                  Past
                </h2>
                <ul className="space-y-3 opacity-80">
                  {past.map((b) => (
                    <BookingRow key={b.id} booking={b} upcoming={false} />
                  ))}
                </ul>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}
