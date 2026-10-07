import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { Link } from "react-router-dom";

import { Pagination } from "../components/Pagination";
import { EmptyState, ErrorState, Spinner } from "../components/States";
import { StatusBadge } from "../components/StatusBadge";
import { useAgentEvents, type ConnectionState } from "../hooks/useAgentEvents";
import { bookingKeys, useAgentBookings, useAgentStats, useDecideBooking } from "../hooks/useBookings";
import { useToast } from "../hooks/useToast";
import { errorMessage } from "../lib/errors";
import { formatDateTime } from "../lib/time";
import type { AgentBooking, AgentEvent, BookingStatus } from "../types/api";

const TABS: { label: string; status: BookingStatus | undefined }[] = [
  { label: "Pending", status: "pending" },
  { label: "Accepted", status: "accepted" },
  { label: "Rejected", status: "rejected" },
  { label: "Cancelled", status: "cancelled" },
  { label: "All", status: undefined },
];

const CONNECTION_LABELS: Record<ConnectionState, { text: string; dot: string }> = {
  connecting: { text: "Connecting…", dot: "bg-slate-400" },
  live: { text: "Live", dot: "bg-emerald-500" },
  reconnecting: { text: "Reconnecting…", dot: "bg-amber-500" },
  offline: { text: "Offline", dot: "bg-red-500" },
};

function StatCard({ label, value }: { label: string; value: number | undefined }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-3xl font-bold text-slate-900">{value ?? "–"}</p>
    </div>
  );
}

function DecisionButtons({ booking }: { booking: AgentBooking }) {
  const decide = useDecideBooking();
  const { notify } = useToast();
  if (booking.status !== "pending") return null;

  const run = (status: "accepted" | "rejected") =>
    decide.mutate(
      { id: booking.id, status },
      {
        onSuccess: () => notify({ title: status === "accepted" ? "Visit accepted" : "Visit declined", tone: "success" }),
        onError: (error) => notify({ title: "Couldn't update", description: errorMessage(error), tone: "error" }),
      },
    );

  return (
    <div className="flex gap-2">
      <button
        type="button"
        className="btn-primary bg-emerald-600 px-3 py-1.5 hover:bg-emerald-700"
        disabled={decide.isPending}
        onClick={() => run("accepted")}
        aria-label={`Accept visit from ${booking.buyer.full_name}`}
      >
        Accept
      </button>
      <button
        type="button"
        className="btn-secondary px-3 py-1.5"
        disabled={decide.isPending}
        onClick={() => run("rejected")}
        aria-label={`Reject visit from ${booking.buyer.full_name}`}
      >
        Reject
      </button>
    </div>
  );
}

function BuyerContact({ booking }: { booking: AgentBooking }) {
  return (
    <div className="text-sm">
      <p className="font-medium text-slate-900">{booking.buyer.full_name}</p>
      <a href={`mailto:${booking.buyer.email}`} className="block text-brand-700 hover:underline">
        {booking.buyer.email}
      </a>
      {booking.buyer.phone && <p className="text-slate-500">{booking.buyer.phone}</p>}
    </div>
  );
}

export function AgentDashboardPage() {
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const [tab, setTab] = useState(0);
  const [page, setPage] = useState(1);
  const status = TABS[tab]?.status;
  const stats = useAgentStats();
  const bookings = useAgentBookings(status, page);

  const refreshAll = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: bookingKeys.agentAll });
    void queryClient.invalidateQueries({ queryKey: bookingKeys.agentStats });
  }, [queryClient]);

  const onEvent = useCallback(
    (event: AgentEvent) => {
      if (event.type === "booking.created") {
        notify({
          title: "New visit request",
          description: `${event.booking.buyer.full_name} · ${event.booking.listing.title} · ${formatDateTime(event.booking.slot_start)}`,
        });
      } else if (event.type === "booking.cancelled") {
        notify({
          title: "Visit cancelled",
          description: `${event.booking.buyer.full_name} cancelled ${formatDateTime(event.booking.slot_start)}`,
        });
      }
      refreshAll();
    },
    [notify, refreshAll],
  );

  // Events sent while disconnected aren't replayed, so refetch whenever we reconnect.
  const connection = useAgentEvents(onEvent, refreshAll);
  const conn = CONNECTION_LABELS[connection];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-slate-600">Visit requests across your listings.</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-sm text-slate-600 shadow-sm ring-1 ring-slate-200" aria-live="polite">
            <span className={`h-2 w-2 rounded-full ${conn.dot}`} aria-hidden /> {conn.text}
          </span>
          <Link to="/agent/listings/new" className="btn-primary">
            New listing
          </Link>
        </div>
      </div>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <StatCard label="Active listings" value={stats.data?.active_listings} />
        <StatCard label="Pending requests" value={stats.data?.pending_requests} />
        <StatCard label="Upcoming visits" value={stats.data?.upcoming_visits} />
      </div>

      <section aria-labelledby="requests-heading" className="mt-8">
        <h2 id="requests-heading" className="sr-only">
          Visit requests
        </h2>
        <div role="tablist" aria-label="Filter by status" className="flex gap-1 overflow-x-auto border-b border-slate-200">
          {TABS.map((t, i) => (
            <button
              key={t.label}
              type="button"
              role="tab"
              aria-selected={tab === i}
              onClick={() => {
                setTab(i);
                setPage(1);
              }}
              className={`-mb-px shrink-0 border-b-2 px-4 py-2 text-sm font-medium transition ${
                tab === i ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div role="tabpanel" className="mt-4 space-y-4">
          {bookings.isPending ? (
            <div className="flex justify-center py-12">
              <Spinner className="h-8 w-8" />
            </div>
          ) : bookings.isError ? (
            <ErrorState error={bookings.error} onRetry={() => void bookings.refetch()} />
          ) : bookings.data.items.length === 0 ? (
            <EmptyState
              title={status === "pending" ? "No pending requests" : "Nothing here"}
              description={status === "pending" ? "New requests will appear here instantly." : undefined}
            />
          ) : (
            <>
              {/* Table on wide screens, cards on phones. */}
              <div className="hidden overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm md:block">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th scope="col" className="px-4 py-3">Visit</th>
                      <th scope="col" className="px-4 py-3">Listing</th>
                      <th scope="col" className="px-4 py-3">Buyer</th>
                      <th scope="col" className="px-4 py-3">Status</th>
                      <th scope="col" className="px-4 py-3">
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {bookings.data.items.map((b) => (
                      <tr key={b.id} className="align-top">
                        <td className="px-4 py-3 font-medium whitespace-nowrap text-slate-900">{formatDateTime(b.slot_start)}</td>
                        <td className="max-w-xs px-4 py-3">
                          <Link to={`/listings/${b.listing.id}`} className="font-medium text-brand-700 hover:underline">
                            {b.listing.title}
                          </Link>
                          {b.note && <p className="mt-1 text-slate-500 italic">“{b.note}”</p>}
                        </td>
                        <td className="px-4 py-3">
                          <BuyerContact booking={b} />
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge status={b.status} />
                        </td>
                        <td className="px-4 py-3">
                          <DecisionButtons booking={b} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <ul className="space-y-3 md:hidden">
                {bookings.data.items.map((b) => (
                  <li key={b.id} className="space-y-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold">{formatDateTime(b.slot_start)}</span>
                      <StatusBadge status={b.status} />
                    </div>
                    <Link to={`/listings/${b.listing.id}`} className="block text-sm font-medium text-brand-700">
                      {b.listing.title}
                    </Link>
                    {b.note && <p className="text-sm text-slate-500 italic">“{b.note}”</p>}
                    <BuyerContact booking={b} />
                    <DecisionButtons booking={b} />
                  </li>
                ))}
              </ul>

              <Pagination page={bookings.data.page} pageSize={bookings.data.page_size} total={bookings.data.total} onChange={setPage} />
            </>
          )}
        </div>
      </section>
    </div>
  );
}
