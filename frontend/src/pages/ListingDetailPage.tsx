import { lazy, Suspense } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { ImageGallery } from "../components/ImageGallery";
import { EmptyState, ErrorState, PageSpinner, Spinner } from "../components/States";
import { useListing } from "../hooks/useListings";
import { bhkLabel, formatArea, formatPriceFull, formatPriceShort, propertyTypeLabel } from "../lib/format";

const SingleListingMap = lazy(() =>
  import("../components/ListingsMap").then((m) => ({ default: m.SingleListingMap })),
);

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-4 py-3">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-0.5 font-semibold text-slate-900">{value}</dd>
    </div>
  );
}

export function ListingDetailPage() {
  const id = Number(useParams().id);
  const query = useListing(id);

  if (!Number.isInteger(id) || id <= 0 || (query.error instanceof ApiError && query.error.status === 404)) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <EmptyState
          title="Listing not found"
          description="It may have been removed by the agent."
          action={
            <Link to="/listings" className="btn-primary">
              Browse homes
            </Link>
          }
        />
      </div>
    );
  }
  if (query.isPending) return <PageSpinner />;
  if (query.isError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      </div>
    );
  }

  const listing = query.data;
  const bhk = bhkLabel(listing.bhk);
  const pricePerSqft = Math.round(listing.price / listing.area_sqft);

  return (
    <article className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <Link to="/listings" className="text-sm font-medium text-brand-700 hover:underline">
        ← Back to results
      </Link>

      <div className="mt-4 grid gap-8 lg:grid-cols-[1fr_360px]">
        <div className="min-w-0 space-y-8">
          <ImageGallery images={listing.images} title={listing.title} />

          <header className="space-y-2">
            {listing.status !== "active" && (
              <span className="inline-block rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold uppercase text-amber-800">
                {listing.status === "sold" ? "Sold" : "Not currently available"}
              </span>
            )}
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{listing.title}</h1>
            <p className="text-slate-600">{listing.address}</p>
            <p className="text-3xl font-bold text-slate-900">
              {formatPriceShort(listing.price)}
              <span className="ml-3 text-base font-normal text-slate-500">{formatPriceFull(listing.price)}</span>
            </p>
          </header>

          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Fact label="Type" value={propertyTypeLabel(listing.property_type)} />
            {bhk && <Fact label="Bedrooms" value={bhk} />}
            <Fact label="Area" value={formatArea(listing.area_sqft)} />
            <Fact label="Price / sq ft" value={`₹${pricePerSqft.toLocaleString("en-IN")}`} />
          </dl>

          <section>
            <h2 className="mb-2 text-lg font-semibold">About this home</h2>
            <p className="leading-relaxed whitespace-pre-line text-slate-700">{listing.description}</p>
          </section>

          <section>
            <h2 className="mb-3 text-lg font-semibold">Location</h2>
            <p className="mb-3 text-sm text-slate-600">
              {listing.locality}, {listing.city}
            </p>
            <Suspense
              fallback={
                <div className="grid h-72 place-items-center rounded-xl bg-slate-100">
                  <Spinner />
                </div>
              }
            >
              <SingleListingMap latitude={listing.latitude} longitude={listing.longitude} label={listing.title} />
            </Suspense>
          </section>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start">
          <section aria-labelledby="visit-heading" className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 id="visit-heading" className="text-lg font-semibold">
              Book a site visit
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Pick a time the agent has opened and hold it for 5 minutes while you confirm.
            </p>
            {/* Slot picker with hold countdown arrives in Phase 8. */}
            <div data-slot="visit-picker" className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-500">
              Visit slots will appear here.
            </div>
          </section>

          <section aria-labelledby="agent-heading" className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h2 id="agent-heading" className="text-sm font-semibold uppercase tracking-wide text-slate-500">
              Listed by
            </h2>
            <p className="mt-2 font-semibold text-slate-900">{listing.agent.full_name}</p>
            <ul className="mt-2 space-y-1 text-sm">
              <li>
                <a href={`mailto:${listing.agent.email}`} className="text-brand-700 hover:underline">
                  {listing.agent.email}
                </a>
              </li>
              {listing.agent.phone && (
                <li>
                  <a href={`tel:${listing.agent.phone}`} className="text-brand-700 hover:underline">
                    {listing.agent.phone}
                  </a>
                </li>
              )}
            </ul>
          </section>
        </aside>
      </div>
    </article>
  );
}
