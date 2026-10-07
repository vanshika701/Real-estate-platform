import type {
  ListingDetail,
  ListingFilters,
  ListingImage,
  ListingInput,
  ListingSummary,
  Page,
} from "../types/api";
import { apiRequest } from "./client";

export const listingsApi = {
  search: (filters: ListingFilters) =>
    apiRequest<Page<ListingSummary>>("/listings", { query: { ...filters } }),
  get: (id: number) => apiRequest<ListingDetail>(`/listings/${id}`),

  // Agent-only
  mine: (page: number, pageSize: number) =>
    apiRequest<Page<ListingSummary>>("/agent/listings", {
      query: { page, page_size: pageSize },
      auth: true,
    }),
  create: (data: ListingInput) =>
    apiRequest<ListingDetail>("/listings", { method: "POST", body: data, auth: true }),
  update: (id: number, data: Partial<ListingInput>) =>
    apiRequest<ListingDetail>(`/listings/${id}`, { method: "PATCH", body: data, auth: true }),
  remove: (id: number) => apiRequest<undefined>(`/listings/${id}`, { method: "DELETE", auth: true }),
  uploadImage: (id: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiRequest<ListingImage>(`/listings/${id}/images`, {
      method: "POST",
      body: form,
      auth: true,
    });
  },
  deleteImage: (id: number, imageId: number) =>
    apiRequest<undefined>(`/listings/${id}/images/${imageId}`, { method: "DELETE", auth: true }),
};
