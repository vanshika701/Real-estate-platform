import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { resolveImageUrl } from "../api/client";
import { listingsApi } from "../api/listings";
import { Pagination } from "../components/Pagination";
import { EmptyState, ErrorState, PageSpinner, Spinner } from "../components/States";
import { StatusBadge } from "../components/StatusBadge";
import { listingKeys } from "../hooks/useListings";
import { useToast } from "../hooks/useToast";
import { errorMessage } from "../lib/errors";
import { bhkLabel, formatPriceShort, propertyTypeLabel } from "../lib/format";
import type { ListingSummary } from "../types/api";

const PAGE_SIZE = 10;

function ListingRow({ listing }: { listing: ListingSummary }) {
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const [confirming, setConfirming] = useState(false);
  const remove = useMutation({
    mutationFn: () => listingsApi.remove(listing.id),
    onSuccess: () => {
      notify({ title: "Listing deleted", tone: "success" });
      void queryClient.invalidateQueries({ queryKey: listingKeys.all });
    },
    onError: (error) => {
      notify({ title: "Couldn't delete", description: errorMessage(error), tone: "error" });
      setConfirming(false);
    },
  });

  return (
    <li className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center">
      <div className="h-20 w-full shrink-0 overflow-hidden rounded-lg bg-slate-100 sm:w-28">
        {listing.cover_image_url && (
          <img src={resolveImageUrl(listing.cover_image_url)} alt="" className="h-full w-full object-cover" loading="lazy" />
        )}
      </div>
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={listing.status} />
          <span className="font-bold">{formatPriceShort(listing.price)}</span>
        </div>
        <Link to={`/listings/${listing.id}`} className="block truncate font-medium text-slate-900 hover:underline">
          {listing.title}
        </Link>
        <p className="text-sm text-slate-500">
          {[propertyTypeLabel(listing.property_type), bhkLabel(listing.bhk), `${listing.locality}, ${listing.city}`]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>
      <div className="flex shrink-0 gap-2">
        {confirming ? (
          <>
            <button type="button" className="btn-secondary py-2" onClick={() => setConfirming(false)} disabled={remove.isPending}>
              Keep
            </button>
            <button
              type="button"
              className="btn-primary bg-red-600 py-2 hover:bg-red-700"
              onClick={() => remove.mutate()}
              disabled={remove.isPending}
            >
              {remove.isPending && <Spinner className="h-4 w-4 border-white/40 border-t-white" />} Delete forever
            </button>
          </>
        ) : (
          <>
            <Link to={`/agent/listings/${listing.id}/edit`} className="btn-secondary py-2">
              Edit
            </Link>
            <button
              type="button"
              className="btn-secondary py-2 text-red-700"
              onClick={() => setConfirming(true)}
              aria-label={`Delete ${listing.title}`}
            >
              Delete
            </button>
          </>
        )}
      </div>
    </li>
  );
}

export function AgentListingsPage() {
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: [...listingKeys.all, "mine", page],
    queryFn: () => listingsApi.mine(page, PAGE_SIZE),
  });

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">My listings</h1>
          <p className="text-slate-600">Every listing you manage, in any status.</p>
        </div>
        <Link to="/agent/listings/new" className="btn-primary">
          New listing
        </Link>
      </div>

      {query.isPending ? (
        <PageSpinner />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : query.data.items.length === 0 ? (
        <EmptyState
          title="No listings yet"
          description="Create your first listing, then add photos and visit slots."
          action={
            <Link to="/agent/listings/new" className="btn-primary">
              Create a listing
            </Link>
          }
        />
      ) : (
        <div className="space-y-6">
          <ul className="space-y-3">
            {query.data.items.map((listing) => (
              <ListingRow key={listing.id} listing={listing} />
            ))}
          </ul>
          <Pagination page={query.data.page} pageSize={query.data.page_size} total={query.data.total} onChange={setPage} />
        </div>
      )}
    </div>
  );
}
