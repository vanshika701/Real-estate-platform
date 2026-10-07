import { Link } from "react-router-dom";

import { resolveImageUrl } from "../api/client";
import { bhkLabel, formatArea, formatPriceShort, propertyTypeLabel } from "../lib/format";
import type { ListingSummary } from "../types/api";

export function ListingCard({ listing }: { listing: ListingSummary }) {
  const bhk = bhkLabel(listing.bhk);

  return (
    <Link
      to={`/listings/${listing.id}`}
      className="group flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition hover:shadow-md focus-visible:outline-2 focus-visible:outline-brand-600"
    >
      <div className="relative aspect-[4/3] bg-slate-100">
        {listing.cover_image_url ? (
          <img
            src={resolveImageUrl(listing.cover_image_url)}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.02]"
          />
        ) : (
          <div className="grid h-full place-items-center text-sm text-slate-400">No photo yet</div>
        )}
        <span className="absolute top-3 left-3 rounded-full bg-white/90 px-2.5 py-1 text-xs font-medium text-slate-700 shadow-sm">
          {propertyTypeLabel(listing.property_type)}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-1 p-4">
        <p className="text-lg font-bold text-slate-900">{formatPriceShort(listing.price)}</p>
        <h3 className="line-clamp-2 text-sm font-medium text-slate-800">{listing.title}</h3>
        <p className="text-sm text-slate-500">
          {listing.locality}, {listing.city}
        </p>
        <p className="mt-auto pt-2 text-sm text-slate-600">
          {[bhk, formatArea(listing.area_sqft)].filter(Boolean).join(" · ")}
        </p>
      </div>
    </Link>
  );
}

export function ListingCardSkeleton() {
  return (
    <div aria-hidden className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="aspect-[4/3] animate-pulse bg-slate-200" />
      <div className="space-y-2 p-4">
        <div className="h-5 w-24 animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-full animate-pulse rounded bg-slate-200" />
        <div className="h-4 w-2/3 animate-pulse rounded bg-slate-200" />
      </div>
    </div>
  );
}
