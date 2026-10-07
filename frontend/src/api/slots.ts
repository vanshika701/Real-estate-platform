import type { Hold, Slot, SlotInput } from "../types/api";
import { apiRequest } from "./client";

export const slotsApi = {
  list: (listingId: number) => apiRequest<Slot[]>(`/listings/${listingId}/slots`),
  create: (listingId: number, slots: SlotInput[]) =>
    apiRequest<Slot[]>(`/listings/${listingId}/slots`, {
      method: "POST",
      body: { slots },
      auth: true,
    }),
  hold: (listingId: number, slotStart: string) =>
    apiRequest<Hold>(`/listings/${listingId}/slots/hold`, {
      method: "POST",
      body: { slot_start: slotStart },
      auth: true,
    }),
  release: (listingId: number, slotStart: string, keepalive = false) =>
    apiRequest<undefined>(`/listings/${listingId}/slots/hold`, {
      method: "DELETE",
      body: { slot_start: slotStart },
      auth: true,
      keepalive,
    }),
};
