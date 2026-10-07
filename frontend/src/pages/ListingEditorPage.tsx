import { useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { listingsApi } from "../api/listings";
import { ListingForm } from "../components/ListingForm";
import { PhotosManager } from "../components/PhotosManager";
import { SlotsManager } from "../components/SlotsManager";
import { EmptyState, ErrorState, PageSpinner } from "../components/States";
import { useAuth } from "../hooks/useAuth";
import { listingKeys, useListing } from "../hooks/useListings";
import { useToast } from "../hooks/useToast";
import { errorMessage } from "../lib/errors";
import { listingSchema, type ListingFormValues } from "../lib/listingSchema";
import type { ListingDetail, ListingInput } from "../types/api";

/** Just the editable fields, as the form expects them. */
function formValuesOf(listing: ListingDetail): ListingFormValues {
  const keys = Object.keys(listingSchema.shape) as (keyof ListingFormValues)[];
  return Object.fromEntries(keys.map((k) => [k, listing[k]])) as ListingFormValues;
}

function Card({ children }: { children: ReactNode }) {
  return <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">{children}</div>;
}

export function NewListingPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { notify } = useToast();

  const create = async (values: Partial<ListingInput>) => {
    try {
      const listing = await listingsApi.create(values as ListingInput);
      void queryClient.invalidateQueries({ queryKey: listingKeys.all });
      notify({ title: "Listing created", description: "Now add photos and visit slots.", tone: "success" });
      navigate(`/agent/listings/${listing.id}/edit`, { replace: true });
    } catch (error) {
      notify({ title: "Couldn't create listing", description: errorMessage(error), tone: "error" });
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <Link to="/agent/listings" className="text-sm font-medium text-brand-700 hover:underline">
        ← My listings
      </Link>
      <h1 className="mt-2 mb-6 text-2xl font-bold tracking-tight">New listing</h1>
      <Card>
        <ListingForm submitLabel="Create listing" onSubmit={create} />
      </Card>
    </div>
  );
}

export function EditListingPage() {
  const id = Number(useParams().id);
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const { notify } = useToast();
  const query = useListing(id);

  if (query.isPending) return <PageSpinner />;
  if (query.isError) {
    const notFound = query.error instanceof ApiError && query.error.status === 404;
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        {notFound ? <EmptyState title="Listing not found" /> : <ErrorState error={query.error} onRetry={() => void query.refetch()} />}
      </div>
    );
  }

  const listing = query.data;
  if (listing.agent_id !== user?.id) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <EmptyState title="Not your listing" description="You can only edit listings you created." />
      </div>
    );
  }

  const save = async (changes: Partial<ListingInput>) => {
    try {
      const updated = await listingsApi.update(listing.id, changes);
      queryClient.setQueryData(listingKeys.detail(listing.id), updated);
      void queryClient.invalidateQueries({ queryKey: listingKeys.all });
      notify({ title: "Changes saved", tone: "success" });
    } catch (error) {
      notify({ title: "Couldn't save", description: errorMessage(error), tone: "error" });
      throw error; // keep the form dirty so nothing looks saved
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6 px-4 py-8 sm:px-6">
      <div>
        <Link to="/agent/listings" className="text-sm font-medium text-brand-700 hover:underline">
          ← My listings
        </Link>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-bold tracking-tight">Edit listing</h1>
          <Link to={`/listings/${listing.id}`} className="btn-secondary py-2">
            View public page
          </Link>
        </div>
      </div>
      <Card>
        <PhotosManager listingId={listing.id} images={listing.images} />
      </Card>
      <Card>
        <SlotsManager listingId={listing.id} />
      </Card>
      <Card>
        <h2 className="mb-4 text-lg font-semibold">Details</h2>
        <ListingForm key={listing.updated_at} defaultValues={formValuesOf(listing)} submitLabel="Save changes" showStatus onSubmit={save} />
      </Card>
    </div>
  );
}
