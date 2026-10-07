import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState, type FormEvent } from "react";

import { slotsApi } from "../api/slots";
import { slotKeys, useSlots } from "../hooks/useBookings";
import { useToast } from "../hooks/useToast";
import { errorMessage } from "../lib/errors";
import { addDays, dayKey, formatDay, formatTime, istToIso, todayInIst } from "../lib/time";
import { buildSlots } from "../lib/slots";
import type { Slot } from "../types/api";
import { Spinner } from "./States";

const TIME_CHOICES = ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00", "18:00"];
const DURATIONS = [30, 45, 60, 90];

function label(time: string): string {
  return formatTime(istToIso("2030-01-01", time));
}

export function SlotsManager({ listingId }: { listingId: number }) {
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const slots = useSlots(listingId);
  const [startDate, setStartDate] = useState(() => addDays(todayInIst(), 1));
  const [days, setDays] = useState(7);
  const [times, setTimes] = useState<string[]>(["10:00", "15:00"]);
  const [minutes, setMinutes] = useState(60);
  const [error, setError] = useState<string | null>(null);

  const preview = useMemo(() => buildSlots(startDate, days, times, minutes), [startDate, days, times, minutes]);

  const create = useMutation({
    mutationFn: () => slotsApi.create(listingId, preview),
    onMutate: () => setError(null),
    onSuccess: (created) => {
      notify({ title: `${created.length} visit slots added`, tone: "success" });
      void queryClient.invalidateQueries({ queryKey: slotKeys.forListing(listingId) });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const toggleTime = (time: string) =>
    setTimes((current) => (current.includes(time) ? current.filter((t) => t !== time) : [...current, time]));

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (preview.length === 0) {
      setError("Pick at least one time.");
      return;
    }
    create.mutate();
  };

  const upcomingByDay = useMemo(() => {
    const groups = new Map<string, Slot[]>();
    for (const slot of slots.data ?? []) {
      const key = dayKey(slot.slot_start);
      groups.set(key, [...(groups.get(key) ?? []), slot]);
    }
    return [...groups.entries()];
  }, [slots.data]);

  return (
    <section aria-labelledby="slots-heading" className="space-y-5">
      <div>
        <h2 id="slots-heading" className="text-lg font-semibold">Visit slots</h2>
        <p className="text-sm text-slate-500">Times are in IST. Buyers can book any open slot.</p>
      </div>

      <form onSubmit={submit} aria-label="Add visit slots" className="space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label htmlFor="slots-start" className="label">Starting</label>
            <input
              id="slots-start"
              type="date"
              className="input"
              min={todayInIst()}
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </div>
          <div>
            <label htmlFor="slots-days" className="label">For how many days</label>
            <select id="slots-days" className="input" value={days} onChange={(e) => setDays(Number(e.target.value))}>
              {[1, 3, 5, 7, 14].map((n) => (
                <option key={n} value={n}>{n} day{n === 1 ? "" : "s"}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="slots-duration" className="label">Each visit lasts</label>
            <select id="slots-duration" className="input" value={minutes} onChange={(e) => setMinutes(Number(e.target.value))}>
              {DURATIONS.map((m) => (
                <option key={m} value={m}>{m} min</option>
              ))}
            </select>
          </div>
        </div>

        <fieldset>
          <legend className="label">Start times</legend>
          <div className="flex flex-wrap gap-2">
            {TIME_CHOICES.map((time) => {
              const on = times.includes(time);
              return (
                <button
                  key={time}
                  type="button"
                  aria-pressed={on}
                  onClick={() => toggleTime(time)}
                  className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition ${
                    on ? "border-brand-600 bg-brand-600 text-white" : "border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
                  }`}
                >
                  {label(time)}
                </button>
              );
            })}
          </div>
        </fieldset>

        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-slate-600" aria-live="polite">
            Creates <strong>{preview.length}</strong> slot{preview.length === 1 ? "" : "s"}
          </p>
          <button type="submit" className="btn-primary" disabled={create.isPending || preview.length === 0}>
            {create.isPending && <Spinner className="h-4 w-4 border-white/40 border-t-white" />} Add slots
          </button>
        </div>
      </form>

      <div>
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Upcoming slots</h3>
        {slots.isPending ? (
          <Spinner />
        ) : upcomingByDay.length === 0 ? (
          <p className="text-sm text-slate-500">No upcoming slots. Add some above so buyers can book.</p>
        ) : (
          <ul className="space-y-2">
            {upcomingByDay.map(([key, list]) => (
              <li key={key} className="flex flex-wrap items-center gap-2 text-sm">
                <span className="w-28 shrink-0 font-medium text-slate-700">{list[0] ? formatDay(list[0].slot_start) : key}</span>
                {list.map((slot) => (
                  <span
                    key={slot.id}
                    className={`rounded-md px-2 py-0.5 text-xs font-medium ${
                      slot.status === "booked"
                        ? "bg-emerald-100 text-emerald-800"
                        : slot.status === "held"
                          ? "bg-amber-100 text-amber-800"
                          : "bg-white text-slate-700 ring-1 ring-slate-200"
                    }`}
                    title={slot.status}
                  >
                    {formatTime(slot.slot_start)}
                    {slot.status !== "available" && ` · ${slot.status}`}
                  </span>
                ))}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
