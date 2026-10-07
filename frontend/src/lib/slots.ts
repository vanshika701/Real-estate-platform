import type { SlotInput } from "../types/api";
import { addDays, istToIso } from "./time";

/** Expand the form into concrete slots: every chosen time on each of the next N days. */
export function buildSlots(startDate: string, days: number, times: string[], minutes: number): SlotInput[] {
  const slots: SlotInput[] = [];
  for (let d = 0; d < days; d++) {
    const date = addDays(startDate, d);
    for (const time of [...times].sort()) {
      const start = istToIso(date, time);
      const end = new Date(new Date(start).getTime() + minutes * 60_000).toISOString();
      slots.push({ slot_start: start, slot_end: end });
    }
  }
  return slots;
}
