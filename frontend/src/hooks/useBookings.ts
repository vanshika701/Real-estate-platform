import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { agentApi, bookingsApi } from "../api/bookings";
import { slotsApi } from "../api/slots";
import type { BookingStatus } from "../types/api";

export const bookingKeys = {
  mine: ["bookings", "mine"] as const,
  agentAll: ["agent", "bookings"] as const,
  agentList: (status: BookingStatus | undefined, page: number) =>
    ["agent", "bookings", status ?? "all", page] as const,
  agentStats: ["agent", "stats"] as const,
};

export const slotKeys = {
  forListing: (listingId: number) => ["slots", listingId] as const,
};

export function useSlots(listingId: number) {
  return useQuery({
    queryKey: slotKeys.forListing(listingId),
    queryFn: () => slotsApi.list(listingId),
    // Other buyers hold and book slots too; poll so the picker doesn't go stale.
    refetchInterval: 20_000,
  });
}

export function useMyBookings() {
  return useQuery({ queryKey: bookingKeys.mine, queryFn: bookingsApi.mine });
}

export function useCancelBooking() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: bookingsApi.cancel,
    onSuccess: (booking) => {
      void queryClient.invalidateQueries({ queryKey: bookingKeys.mine });
      void queryClient.invalidateQueries({ queryKey: slotKeys.forListing(booking.listing_id) });
    },
  });
}

export function useAgentBookings(status: BookingStatus | undefined, page: number) {
  return useQuery({
    queryKey: bookingKeys.agentList(status, page),
    queryFn: () => agentApi.bookings({ status, page, page_size: 10 }),
  });
}

export function useAgentStats() {
  return useQuery({ queryKey: bookingKeys.agentStats, queryFn: agentApi.stats });
}

export function useDecideBooking() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: "accepted" | "rejected" }) =>
      agentApi.decide(id, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: bookingKeys.agentAll });
      void queryClient.invalidateQueries({ queryKey: bookingKeys.agentStats });
    },
  });
}
