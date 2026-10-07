import type { AgentBooking, AgentStats, Booking, BookingStatus, Page } from "../types/api";
import { apiRequest } from "./client";

export const bookingsApi = {
  create: (data: { listing_id: number; slot_start: string; note?: string | null }) =>
    apiRequest<Booking>("/bookings", { method: "POST", body: data, auth: true }),
  mine: () => apiRequest<Booking[]>("/bookings/me", { auth: true }),
  cancel: (id: number) =>
    apiRequest<Booking>(`/bookings/${id}/cancel`, { method: "PATCH", auth: true }),
};

export const agentApi = {
  bookings: (params: { status?: BookingStatus; page?: number; page_size?: number }) =>
    apiRequest<Page<AgentBooking>>("/agent/bookings", { query: { ...params }, auth: true }),
  decide: (id: number, status: "accepted" | "rejected") =>
    apiRequest<AgentBooking>(`/agent/bookings/${id}`, {
      method: "PATCH",
      body: { status },
      auth: true,
    }),
  stats: () => apiRequest<AgentStats>("/agent/stats", { auth: true }),
};
