/** Types mirroring the backend's Pydantic schemas. */

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
  };
}

export type DependencyStatus = "ok" | "error";

export interface HealthResponse {
  status: "ok" | "degraded";
  checks: Record<string, DependencyStatus>;
}

// --- auth ---

export type UserRole = "buyer" | "agent";

export interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
  role: UserRole;
  created_at: string;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface AuthResponse extends Tokens {
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest extends LoginRequest {
  full_name: string;
  role: UserRole;
  phone?: string | null;
}

// --- listings ---

export const PROPERTY_TYPES = ["apartment", "villa", "plot", "independent_house"] as const;
export type PropertyType = (typeof PROPERTY_TYPES)[number];

export const LISTING_SORTS = ["newest", "price_asc", "price_desc"] as const;
export type ListingSort = (typeof LISTING_SORTS)[number];

export type ListingStatus = "active" | "sold" | "inactive";

export interface ListingSummary {
  id: number;
  title: string;
  city: string;
  locality: string;
  latitude: number;
  longitude: number;
  price: number;
  bhk: number;
  area_sqft: number;
  property_type: PropertyType;
  status: ListingStatus;
  cover_image_url: string | null;
  created_at: string;
}

export interface ListingImage {
  id: number;
  url: string;
  position: number;
}

export interface AgentContact {
  id: number;
  full_name: string;
  email: string;
  phone: string | null;
}

export interface ListingDetail extends Omit<ListingSummary, "cover_image_url"> {
  agent_id: number;
  description: string;
  address: string;
  updated_at: string;
  images: ListingImage[];
  agent: AgentContact;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ListingFilters {
  city?: string;
  min_price?: number;
  max_price?: number;
  bhk?: number;
  property_type?: PropertyType;
  sort?: ListingSort;
  page?: number;
  page_size?: number;
}

export interface ListingInput {
  title: string;
  description: string;
  city: string;
  locality: string;
  address: string;
  latitude: number;
  longitude: number;
  price: number;
  bhk: number;
  area_sqft: number;
  property_type: PropertyType;
  status?: ListingStatus;
}

// --- slots & holds ---

export type SlotStatus = "available" | "held" | "booked";

export interface Slot {
  id: number;
  slot_start: string;
  slot_end: string;
  status: SlotStatus;
}

export interface SlotInput {
  slot_start: string;
  slot_end: string;
}

export interface Hold {
  listing_id: number;
  slot_start: string;
  expires_at: string;
  /** Seconds left on the hold when the server responded. */
  expires_in: number;
}

// --- bookings ---

export type BookingStatus = "pending" | "accepted" | "rejected" | "cancelled";

export interface BookingListing {
  id: number;
  title: string;
  city: string;
  locality: string;
  address: string;
}

export interface Booking {
  id: number;
  listing_id: number;
  slot_start: string;
  status: BookingStatus;
  note: string | null;
  created_at: string;
  listing: BookingListing;
}

export interface AgentBooking extends Booking {
  buyer: AgentContact;
}

export interface AgentStats {
  active_listings: number;
  pending_requests: number;
  upcoming_visits: number;
}

export type AgentEvent =
  | { type: "booking.created"; booking: AgentBooking }
  | { type: "booking.cancelled"; booking: AgentBooking }
  | { type: "ping" };
