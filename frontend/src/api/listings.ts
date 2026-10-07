import type { ListingDetail, ListingFilters, ListingSummary, Page } from "../types/api";
import { apiRequest } from "./client";

export const listingsApi = {
  search: (filters: ListingFilters) =>
    apiRequest<Page<ListingSummary>>("/listings", { query: { ...filters } }),
  get: (id: number) => apiRequest<ListingDetail>(`/listings/${id}`),
};
