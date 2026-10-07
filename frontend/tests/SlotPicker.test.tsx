import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { bookingsApi } from "../src/api/bookings";
import { ApiError } from "../src/api/client";
import { slotsApi } from "../src/api/slots";
import { SlotPicker } from "../src/components/SlotPicker";
import type { Booking, Hold, Slot, User } from "../src/types/api";
import { agent, buyer, currentLocation, renderWithProviders } from "./utils";

vi.mock("../src/api/slots", () => ({
  slotsApi: { list: vi.fn(), hold: vi.fn(), release: vi.fn(), create: vi.fn() },
}));
vi.mock("../src/api/bookings", () => ({
  bookingsApi: { create: vi.fn(), mine: vi.fn(), cancel: vi.fn() },
  agentApi: {},
}));

const list = vi.mocked(slotsApi.list);
const hold = vi.mocked(slotsApi.hold);
const release = vi.mocked(slotsApi.release);
const createBooking = vi.mocked(bookingsApi.create);

// 10:00, 12:00 and 15:00 IST on 9 Oct, plus 10:00 IST on 10 Oct.
const OPEN: Slot = { id: 1, slot_start: "2030-10-09T04:30:00Z", slot_end: "2030-10-09T05:30:00Z", status: "available" };
const HELD: Slot = { id: 2, slot_start: "2030-10-09T06:30:00Z", slot_end: "2030-10-09T07:30:00Z", status: "held" };
const BOOKED: Slot = { id: 3, slot_start: "2030-10-09T09:30:00Z", slot_end: "2030-10-09T10:30:00Z", status: "booked" };
const NEXT_DAY: Slot = { id: 4, slot_start: "2030-10-10T04:30:00Z", slot_end: "2030-10-10T05:30:00Z", status: "available" };
const SLOTS = [OPEN, HELD, BOOKED, NEXT_DAY];

function holdFor(slot: Slot, expiresIn = 300): Hold {
  return { listing_id: 7, slot_start: slot.slot_start, expires_at: "", expires_in: expiresIn };
}

const renderPicker = (user: User | null = buyer, acceptingVisits = true) =>
  renderWithProviders(<SlotPicker listingId={7} acceptingVisits={acceptingVisits} />, {
    route: "/listings/7",
    path: "/listings/:id",
    user,
  });

/** The time grid, once slots have loaded. */
const times = async () => within(await screen.findByRole("tabpanel", { name: "Times" }));

describe("<SlotPicker>", () => {
  beforeEach(() => {
    list.mockResolvedValue(SLOTS);
    release.mockResolvedValue(undefined);
  });

  it("groups slots by IST day and shows each slot's status", async () => {
    renderPicker();

    expect(await screen.findByRole("tab", { name: /Wed, 9 Oct\s*1 open/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: /Thu, 10 Oct\s*1 open/ })).toBeInTheDocument();
    expect((await times()).getByRole("button", { name: "10:00 am, available" })).toBeEnabled();
    expect((await times()).getByRole("button", { name: "12:00 pm, on hold" })).toBeDisabled();
    expect((await times()).getByRole("button", { name: "3:00 pm, booked" })).toBeDisabled();
  });

  it("holds a slot and starts a 5:00 countdown", async () => {
    hold.mockResolvedValue(holdFor(OPEN));
    renderPicker();

    await userEvent.click((await times()).getByRole("button", { name: "10:00 am, available" }));

    expect(hold).toHaveBeenCalledWith(7, OPEN.slot_start);
    expect(await screen.findByRole("timer")).toHaveTextContent("5:00");
    expect((await times()).getByRole("button", { name: "10:00 am, your hold" })).toHaveAttribute("aria-pressed", "true");
  });

  it("confirms the held slot with the note and shows success", async () => {
    hold.mockResolvedValue(holdFor(OPEN));
    createBooking.mockResolvedValue({ id: 99, slot_start: OPEN.slot_start } as Booking);
    renderPicker();

    await userEvent.click((await times()).getByRole("button", { name: "10:00 am, available" }));
    await userEvent.type(await screen.findByLabelText(/Note for the agent/), "  Bringing family  ");
    await userEvent.click(screen.getByRole("button", { name: "Confirm visit" }));

    expect(createBooking).toHaveBeenCalledWith({ listing_id: 7, slot_start: OPEN.slot_start, note: "Bringing family" });
    expect(await screen.findByText("Visit requested!")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View my bookings" })).toHaveAttribute("href", "/my-bookings");
  });

  it("releases the previous hold when switching slots", async () => {
    hold.mockResolvedValueOnce(holdFor(OPEN)).mockResolvedValueOnce(holdFor(NEXT_DAY));
    renderPicker();

    await userEvent.click((await times()).getByRole("button", { name: "10:00 am, available" }));
    await screen.findByRole("timer");
    await userEvent.click(screen.getByRole("tab", { name: /Thu, 10 Oct/ }));
    await userEvent.click((await times()).getByRole("button", { name: "10:00 am, available" }));

    await waitFor(() => expect(hold).toHaveBeenCalledTimes(2));
    expect(release).toHaveBeenCalledWith(7, OPEN.slot_start);
  });

  it("explains when another buyer got the slot first", async () => {
    hold.mockRejectedValue(new ApiError(409, "slot_held", "held"));
    renderPicker();

    await userEvent.click((await times()).getByRole("button", { name: "10:00 am, available" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Someone else is booking that slot right now");
    expect(screen.queryByRole("timer")).not.toBeInTheDocument();
  });

  it("disables confirming once the hold expires", async () => {
    hold.mockResolvedValue(holdFor(OPEN, 1)); // a 1-second hold
    renderPicker();

    await userEvent.click((await times()).getByRole("button", { name: "10:00 am, available" }));
    expect(await screen.findByRole("timer")).toHaveTextContent("0:01");

    expect(await screen.findByText("Your hold expired", {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm visit" })).not.toBeInTheDocument();
  });

  it("asks for a fresh hold if the server says it lapsed", async () => {
    hold.mockResolvedValue(holdFor(OPEN));
    createBooking.mockRejectedValue(new ApiError(409, "hold_required", "expired"));
    renderPicker();

    await userEvent.click((await times()).getByRole("button", { name: "10:00 am, available" }));
    await userEvent.click(await screen.findByRole("button", { name: "Confirm visit" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Your hold expired before you confirmed");
  });

  it("sends signed-out visitors to log in, then back to the listing", async () => {
    renderPicker(null);

    await userEvent.click((await times()).getByRole("button", { name: "10:00 am, available" }));

    expect(hold).not.toHaveBeenCalled();
    expect(currentLocation()).toBe("/login?next=%2Flistings%2F7");
  });

  it("is read-only for agents", async () => {
    renderPicker(agent);

    expect(await screen.findByText(/signed in as an agent/)).toBeInTheDocument();
    expect((await times()).getByRole("button", { name: "10:00 am, available" })).toBeDisabled();
  });

  it("says so when the listing isn't taking visits", () => {
    renderPicker(buyer, false);

    expect(screen.getByText("This home isn't taking visits right now.")).toBeInTheDocument();
    expect(list).not.toHaveBeenCalled();
  });
});
