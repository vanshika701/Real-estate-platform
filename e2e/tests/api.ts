/** Test setup through the public API, so each run starts from known, isolated data. */
import { expect, type APIRequestContext } from "@playwright/test";

export const DEMO_AGENT = { email: "agent@demo.com", password: "Demo@1234" };

export async function login(request: APIRequestContext, email: string, password: string): Promise<string> {
  const response = await request.post("/api/v1/auth/login", { data: { email, password } });
  expect(response.ok(), await response.text()).toBeTruthy();
  return ((await response.json()) as { access_token: string }).access_token;
}

const auth = (token: string) => ({ Authorization: `Bearer ${token}` });

/** Tomorrow's date in India, as YYYY-MM-DD. */
function tomorrowInIst(): string {
  const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(tomorrow);
}

export interface TestListing {
  id: number;
  title: string;
  city: string;
}

/** A fresh listing owned by the demo agent, with three slots tomorrow (IST). */
export async function createListingWithSlots(request: APIRequestContext, agentToken: string): Promise<TestListing> {
  const title = `E2E Garden Villa ${Date.now()}`;
  const city = "Pune";
  const created = await request.post("/api/v1/listings", {
    headers: auth(agentToken),
    data: {
      title,
      description: "Created by the end-to-end test suite.",
      city,
      locality: "Baner",
      address: "Plot 7, Palm Grove, Baner, Pune",
      latitude: 18.559,
      longitude: 73.7868,
      price: 32_500_000,
      bhk: 4,
      area_sqft: 3200,
      property_type: "villa",
    },
  });
  expect(created.ok(), await created.text()).toBeTruthy();
  const { id } = (await created.json()) as { id: number };

  const day = tomorrowInIst();
  const slots = ["11:00", "14:00", "16:00"].map((time) => {
    const start = new Date(`${day}T${time}:00+05:30`);
    return { slot_start: start.toISOString(), slot_end: new Date(start.getTime() + 3_600_000).toISOString() };
  });
  const slotResponse = await request.post(`/api/v1/listings/${id}/slots`, { headers: auth(agentToken), data: { slots } });
  expect(slotResponse.ok(), await slotResponse.text()).toBeTruthy();

  return { id, title, city };
}

export async function deleteListing(request: APIRequestContext, agentToken: string, id: number): Promise<void> {
  await request.delete(`/api/v1/listings/${id}`, { headers: auth(agentToken) });
}

/** Hold and book a slot as a buyer, straight through the API. */
export async function bookViaApi(
  request: APIRequestContext,
  buyerToken: string,
  listingId: number,
): Promise<{ id: number }> {
  const slots = (await (await request.get(`/api/v1/listings/${listingId}/slots`)).json()) as {
    slot_start: string;
    status: string;
  }[];
  const open = slots.find((s) => s.status === "available");
  expect(open, "an open slot to book").toBeTruthy();
  const slotStart = open?.slot_start ?? "";
  const held = await request.post(`/api/v1/listings/${listingId}/slots/hold`, {
    headers: auth(buyerToken),
    data: { slot_start: slotStart },
  });
  expect(held.ok(), await held.text()).toBeTruthy();
  const booked = await request.post("/api/v1/bookings", {
    headers: auth(buyerToken),
    data: { listing_id: listingId, slot_start: slotStart },
  });
  expect(booked.ok(), await booked.text()).toBeTruthy();
  return (await booked.json()) as { id: number };
}
