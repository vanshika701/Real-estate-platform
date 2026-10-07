import { lazy, Suspense, useState } from "react";

import { ListingCard, ListingCardSkeleton } from "../components/ListingCard";
import { ListingFilters } from "../components/ListingFilters";
import { Pagination } from "../components/Pagination";
import { EmptyState, ErrorState, PageSpinner, Spinner } from "../components/States";
import { useListingFilters, type ListingView } from "../hooks/useListingFilters";
import { useListingSearch } from "../hooks/useListings";

// Leaflet is ~150 KB; only download it when someone opens the map.
const ListingsMap = lazy(() =>
  import("../components/ListingsMap").then((m) => ({ default: m.ListingsMap })),
);

const PAGE_SIZE = { list: 12, map: 50 } as const;

export function ListingsPage() {
  const { state, update, clear } = useListingFilters();
  const [filtersOpen, setFiltersOpen] = useState(false);
  const { view, ...filters } = state;
  const page = filters.page ?? 1;
  const query = useListingSearch({ ...filters, page, page_size: PAGE_SIZE[view] });

  const activeFilterCount = [filters.city, filters.min_price, filters.max_price, filters.bhk, filters.property_type].filter(
    (v) => v !== undefined,
  ).length;

  const setView = (next: ListingView) => update({ view: next });

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Homes for sale</h1>
          <p className="text-sm text-slate-600" aria-live="polite">
            {query.data ? `${query.data.total} ${query.data.total === 1 ? "home" : "homes"} found` : " "}
            {filters.city ? ` in ${filters.city}` : ""}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="btn-secondary py-2 lg:hidden"
            aria-expanded={filtersOpen}
            aria-controls="filters-panel"
            onClick={() => setFiltersOpen((open) => !open)}
          >
            Filters{activeFilterCount ? ` (${activeFilterCount})` : ""}
          </button>
          <div role="group" aria-label="View" className="inline-flex rounded-lg border border-slate-300 bg-white p-0.5">
            {(["list", "map"] as const).map((v) => (
              <button
                key={v}
                type="button"
                aria-pressed={view === v}
                onClick={() => setView(v)}
                className={`rounded-md px-3 py-1.5 text-sm font-medium capitalize transition ${
                  view === v ? "bg-brand-600 text-white" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {v}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-[260px_1fr]">
        <aside
          id="filters-panel"
          className={`${filtersOpen ? "block" : "hidden"} rounded-xl border border-slate-200 bg-white p-5 lg:sticky lg:top-24 lg:block lg:self-start`}
        >
          <ListingFilters state={state} onChange={update} onClear={clear} />
        </aside>

        <section aria-label="Results" aria-busy={query.isFetching} className="min-w-0 space-y-6">
          {query.isPending ? (
            view === "map" ? (
              <PageSpinner />
            ) : (
              <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: 6 }, (_, i) => (
                  <ListingCardSkeleton key={i} />
                ))}
              </div>
            )
          ) : query.isError ? (
            <ErrorState error={query.error} onRetry={() => void query.refetch()} />
          ) : query.data.items.length === 0 ? (
            <EmptyState
              title="No homes match these filters"
              description="Try a different city, widening your budget, or removing a filter."
              action={
                <button type="button" className="btn-secondary" onClick={clear}>
                  Clear filters
                </button>
              }
            />
          ) : (
            <>
              {query.isFetching && (
                <div className="flex items-center gap-2 text-sm text-slate-500">
                  <Spinner className="h-4 w-4" /> Updating…
                </div>
              )}
              {view === "map" ? (
                <Suspense fallback={<PageSpinner />}>
                  <ListingsMap listings={query.data.items} />
                </Suspense>
              ) : (
                <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
                  {query.data.items.map((listing) => (
                    <ListingCard key={listing.id} listing={listing} />
                  ))}
                </div>
              )}
              <Pagination
                page={query.data.page}
                pageSize={query.data.page_size}
                total={query.data.total}
                onChange={(p) => {
                  update({ page: p });
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
              />
            </>
          )}
        </section>
      </div>
    </div>
  );
}
