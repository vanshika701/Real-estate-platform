import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { listingsApi } from "../api/listings";
import type { ListingFilters } from "../types/api";

export const listingKeys = {
  all: ["listings"] as const,
  search: (filters: ListingFilters) => ["listings", "search", filters] as const,
  detail: (id: number) => ["listings", "detail", id] as const,
};

export function useListingSearch(filters: ListingFilters) {
  return useQuery({
    queryKey: listingKeys.search(filters),
    queryFn: () => listingsApi.search(filters),
    // Keep showing the previous page while the next loads, instead of flashing a spinner.
    placeholderData: keepPreviousData,
  });
}

export function useListing(id: number) {
  return useQuery({
    queryKey: listingKeys.detail(id),
    queryFn: () => listingsApi.get(id),
    enabled: Number.isInteger(id) && id > 0,
  });
}
