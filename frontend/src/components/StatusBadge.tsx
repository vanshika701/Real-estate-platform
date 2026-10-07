import type { BookingStatus, ListingStatus } from "../types/api";

const STYLES: Record<BookingStatus | ListingStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  accepted: "bg-emerald-100 text-emerald-800",
  rejected: "bg-red-100 text-red-700",
  cancelled: "bg-slate-200 text-slate-700",
  active: "bg-emerald-100 text-emerald-800",
  sold: "bg-brand-100 text-brand-800",
  inactive: "bg-slate-200 text-slate-700",
};

export function StatusBadge({ status }: { status: BookingStatus | ListingStatus }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${STYLES[status]}`}>
      {status}
    </span>
  );
}
