import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { listingsApi } from "../src/api/listings";
import { ListingFilters } from "../src/components/ListingFilters";
import { ListingsPage } from "../src/pages/ListingsPage";
import type { ListingSummary, Page } from "../src/types/api";
import { currentLocation, renderWithProviders } from "./utils";

vi.mock("../src/api/listings", () => ({ listingsApi: { search: vi.fn() } }));
const search = vi.mocked(listingsApi.search);

function listing(id: number, overrides: Partial<ListingSummary> = {}): ListingSummary {
  return {
    id,
    title: `Listing ${id}`,
    city: "Pune",
    locality: "Baner",
    latitude: 18.55,
    longitude: 73.78,
    price: 8_000_000,
    bhk: 2,
    area_sqft: 1000,
    property_type: "apartment",
    status: "active",
    cover_image_url: null,
    created_at: "2026-10-01T00:00:00Z",
    ...overrides,
  };
}

function page(items: ListingSummary[], total = items.length): Page<ListingSummary> {
  return { items, total, page: 1, page_size: 12 };
}

describe("<ListingFilters>", () => {
  const renderFilters = (state = {}) => {
    const onChange = vi.fn();
    const onClear = vi.fn();
    renderWithProviders(<ListingFilters state={{ view: "list", ...state }} onChange={onChange} onClear={onClear} />);
    return { onChange, onClear };
  };

  it("toggles a BHK filter on and off", async () => {
    const { onChange } = renderFilters({ bhk: 2 });

    await userEvent.click(screen.getByRole("button", { name: "3 BHK" }));
    expect(onChange).toHaveBeenLastCalledWith({ bhk: 3 });

    await userEvent.click(screen.getByRole("button", { name: "2 BHK" }));
    expect(onChange).toHaveBeenLastCalledWith({ bhk: undefined });
    expect(screen.getByRole("button", { name: "2 BHK" })).toHaveAttribute("aria-pressed", "true");
  });

  it("applies the city on Enter, trimmed, and not on every keystroke", async () => {
    const { onChange } = renderFilters();

    await userEvent.type(screen.getByLabelText("City"), "  Pune ");
    expect(onChange).not.toHaveBeenCalled();

    await userEvent.keyboard("{Enter}");
    expect(onChange).toHaveBeenCalledWith({ city: "Pune" });
  });

  it("flags a minimum price above the maximum", () => {
    renderFilters({ min_price: 20_000_000, max_price: 10_000_000 });

    expect(screen.getByText("Minimum is higher than maximum.")).toBeInTheDocument();
    expect(screen.getByLabelText("Maximum price")).toHaveAttribute("aria-invalid", "true");
  });

  it("changes sort and property type", async () => {
    const { onChange } = renderFilters();

    await userEvent.selectOptions(screen.getByLabelText("Sort by"), "price_asc");
    expect(onChange).toHaveBeenLastCalledWith({ sort: "price_asc" });

    await userEvent.selectOptions(screen.getByLabelText("Property type"), "villa");
    expect(onChange).toHaveBeenLastCalledWith({ property_type: "villa" });
  });
});

describe("<ListingsPage> URL sync", () => {
  beforeEach(() => {
    search.mockResolvedValue(page([listing(1), listing(2)]));
  });

  it("searches with the filters from the URL", async () => {
    renderWithProviders(<ListingsPage />, { route: "/listings?city=Pune&bhk=2&sort=price_asc" });

    expect(await screen.findByText("Listing 1")).toBeInTheDocument();
    expect(search).toHaveBeenCalledWith({ city: "Pune", bhk: 2, sort: "price_asc", page: 1, page_size: 12 });
    expect(screen.getByText(/2 homes found/)).toBeInTheDocument();
  });

  it("writes filter changes back to the URL and resets to page 1", async () => {
    renderWithProviders(<ListingsPage />, { route: "/listings?city=Pune&page=3" });
    await screen.findByText("Listing 1");

    await userEvent.click(screen.getByRole("button", { name: "4 BHK" }));

    await waitFor(() => expect(currentLocation()).toBe("/listings?city=Pune&bhk=4"));
    expect(search).toHaveBeenLastCalledWith({ city: "Pune", bhk: 4, page: 1, page_size: 12 });
  });

  it("ignores invalid params rather than erroring", async () => {
    renderWithProviders(<ListingsPage />, { route: "/listings?bhk=lots&page=zero" });
    await screen.findByText("Listing 1");

    expect(search).toHaveBeenCalledWith({ page: 1, page_size: 12 });
  });

  it("shows an empty state that clears filters", async () => {
    search.mockResolvedValue(page([]));
    renderWithProviders(<ListingsPage />, { route: "/listings?city=Atlantis" });

    expect(await screen.findByText("No homes match these filters")).toBeInTheDocument();
    const results = within(screen.getByRole("region", { name: "Results" }));
    await userEvent.click(results.getByRole("button", { name: "Clear filters" }));

    await waitFor(() => expect(currentLocation()).toBe("/listings"));
  });

  it("shows an error state with retry", async () => {
    search.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    renderWithProviders(<ListingsPage />, { route: "/listings" });

    expect(await screen.findByText(/Can't reach the server/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Listing 1")).toBeInTheDocument();
  });

  it("uses a larger page for the map view", async () => {
    renderWithProviders(<ListingsPage />, { route: "/listings?view=map" });

    await waitFor(() => expect(search).toHaveBeenCalledWith({ page: 1, page_size: 50 }));
  });
});
