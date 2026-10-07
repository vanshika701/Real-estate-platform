/**
 * All visits happen in India, so times are always shown in IST regardless of the viewer's
 * own timezone, and times agents type in are read as IST. India has no DST, so +05:30 is exact.
 */
export const TIME_ZONE = "Asia/Kolkata";
const IST_OFFSET = "+05:30";

const dayKeyFormat = new Intl.DateTimeFormat("en-CA", {
  timeZone: TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});
const dayLabelFormat = new Intl.DateTimeFormat("en-IN", {
  timeZone: TIME_ZONE,
  weekday: "short",
  day: "numeric",
  month: "short",
});
const timeFormat = new Intl.DateTimeFormat("en-IN", {
  timeZone: TIME_ZONE,
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
});
const dateTimeFormat = new Intl.DateTimeFormat("en-IN", {
  timeZone: TIME_ZONE,
  weekday: "short",
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
});

/** "2026-10-09": the IST calendar day, usable as a grouping key. */
export const dayKey = (iso: string) => dayKeyFormat.format(new Date(iso));
/** "Fri, 9 Oct" */
export const formatDay = (iso: string) => dayLabelFormat.format(new Date(iso));
/** "10:00 am" */
export const formatTime = (iso: string) => timeFormat.format(new Date(iso));
/** "Fri, 9 Oct 2026, 10:00 am" */
export const formatDateTime = (iso: string) => dateTimeFormat.format(new Date(iso));

/** "2026-10-09" + "10:00" (IST) → ISO string with an explicit offset. */
export function istToIso(date: string, time: string): string {
  return new Date(`${date}T${time}:00${IST_OFFSET}`).toISOString();
}

/** Today's IST date as YYYY-MM-DD, e.g. for a date input's `min`. */
export const todayInIst = () => dayKeyFormat.format(new Date());

export function addDays(date: string, days: number): string {
  const d = new Date(`${date}T00:00:00${IST_OFFSET}`);
  d.setUTCDate(d.getUTCDate() + days);
  return dayKeyFormat.format(d);
}

export function formatCountdown(seconds: number): string {
  const s = Math.max(0, seconds);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
