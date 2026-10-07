import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ListingCard, ListingCardSkeleton } from "../components/ListingCard";
import { EmptyState, ErrorState } from "../components/States";
import { toSearchParams } from "../hooks/useListingFilters";
import { useListingSearch } from "../hooks/useListings";
import { BHK_OPTIONS, BUDGETS, CITIES } from "../lib/constants";

const FEATURED = { sort: "newest", page_size: 6 } as const;

export function HomePage() {
  const navigate = useNavigate();
  const [city, setCity] = useState("");
  const [budget, setBudget] = useState("");
  const [bhk, setBhk] = useState("");
  const featured = useListingSearch(FEATURED);

  const search = (event: FormEvent) => {
    event.preventDefault();
    const range = budget === "" ? undefined : BUDGETS[Number(budget)];
    const params = toSearchParams({
      city: city.trim() || undefined,
      min_price: range?.min,
      max_price: range?.max,
      bhk: bhk === "" ? undefined : Number(bhk),
    });
    navigate(`/listings?${params.toString()}`);
  };

  return (
    <>
      <section className="bg-gradient-to-br from-brand-700 to-brand-500 text-white">
        <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 sm:py-20">
          <h1 className="max-w-2xl text-3xl font-bold tracking-tight sm:text-5xl">
            Find your next home. Book a visit in minutes.
          </h1>
          <p className="mt-4 max-w-xl text-brand-100 sm:text-lg">
            Verified listings across Delhi NCR, Mumbai, Pune and Bengaluru, with live visit slots
            from the agents themselves.
          </p>

          <form
            onSubmit={search}
            aria-label="Search homes"
            className="mt-8 grid gap-3 rounded-2xl bg-white p-3 text-slate-900 shadow-xl sm:grid-cols-[1.4fr_1fr_0.8fr_auto] sm:p-4"
          >
            <div>
              <label htmlFor="home-city" className="sr-only">
                City
              </label>
              <input
                id="home-city"
                className="input"
                list="home-city-options"
                placeholder="City, e.g. Noida"
                value={city}
                onChange={(e) => setCity(e.target.value)}
              />
              <datalist id="home-city-options">
                {CITIES.map((c) => (
                  <option key={c} value={c} />
                ))}
              </datalist>
            </div>
            <div>
              <label htmlFor="home-budget" className="sr-only">
                Budget
              </label>
              <select id="home-budget" className="input" value={budget} onChange={(e) => setBudget(e.target.value)}>
                <option value="">Any budget</option>
                {BUDGETS.map((b, i) => (
                  <option key={b.label} value={i}>
                    {b.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="home-bhk" className="sr-only">
                Bedrooms
              </label>
              <select id="home-bhk" className="input" value={bhk} onChange={(e) => setBhk(e.target.value)}>
                <option value="">Any BHK</option>
                {BHK_OPTIONS.map((n) => (
                  <option key={n} value={n}>
                    {n} BHK
                  </option>
                ))}
              </select>
            </div>
            <button type="submit" className="btn-primary">
              Search
            </button>
          </form>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <div className="mb-6 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Newly listed</h2>
            <p className="text-slate-600">Fresh on PropVisit this week.</p>
          </div>
          <Link to="/listings" className="text-sm font-semibold text-brand-700 hover:underline">
            View all →
          </Link>
        </div>

        {featured.isPending ? (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }, (_, i) => (
              <ListingCardSkeleton key={i} />
            ))}
          </div>
        ) : featured.isError ? (
          <ErrorState error={featured.error} onRetry={() => void featured.refetch()} />
        ) : featured.data.items.length === 0 ? (
          <EmptyState title="No listings yet" description="Check back soon." />
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {featured.data.items.map((listing) => (
              <ListingCard key={listing.id} listing={listing} />
            ))}
          </div>
        )}
      </section>
    </>
  );
}
