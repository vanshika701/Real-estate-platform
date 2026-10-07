import { describe, expect, it } from "vitest";

import { parseSearchParams, toSearchParams } from "../src/hooks/useListingFilters";
import { formatPriceFull, formatPriceShort } from "../src/lib/format";
import { validateImageFile } from "../src/lib/images";
import { safeNext } from "../src/lib/navigation";
import { buildSlots } from "../src/lib/slots";
import { formatCountdown, istToIso } from "../src/lib/time";

describe("price formatting", () => {
  it.each([
    [4_200_000, "₹42 L"],
    [8_150_000, "₹81.5 L"],
    [10_000_000, "₹1 Cr"],
    [12_550_000, "₹1.25 Cr"],
    [45_800_000, "₹4.58 Cr"],
    [95_000, "₹95,000"],
  ])("formats %d as %s", (price, expected) => {
    expect(formatPriceShort(price)).toBe(expected);
  });

  it("uses Indian digit grouping for full prices", () => {
    expect(formatPriceFull(12_500_000)).toBe("₹1,25,00,000");
  });
});

describe("IST time handling", () => {
  it("reads typed dates and times as IST", () => {
    expect(istToIso("2026-10-09", "10:00")).toBe("2026-10-09T04:30:00.000Z");
  });

  it("builds every chosen time on each day, in order", () => {
    const slots = buildSlots("2026-10-09", 2, ["15:00", "10:00"], 60);

    expect(slots).toEqual([
      { slot_start: "2026-10-09T04:30:00.000Z", slot_end: "2026-10-09T05:30:00.000Z" },
      { slot_start: "2026-10-09T09:30:00.000Z", slot_end: "2026-10-09T10:30:00.000Z" },
      { slot_start: "2026-10-10T04:30:00.000Z", slot_end: "2026-10-10T05:30:00.000Z" },
      { slot_start: "2026-10-10T09:30:00.000Z", slot_end: "2026-10-10T10:30:00.000Z" },
    ]);
  });

  it("crosses month boundaries", () => {
    const [first, second] = buildSlots("2026-10-31", 2, ["10:00"], 30);
    expect(first?.slot_start).toBe("2026-10-31T04:30:00.000Z");
    expect(second?.slot_start).toBe("2026-11-01T04:30:00.000Z");
  });

  it.each([
    [300, "5:00"],
    [61, "1:01"],
    [9, "0:09"],
    [-3, "0:00"],
  ])("formats %d seconds as %s", (seconds, expected) => {
    expect(formatCountdown(seconds)).toBe(expected);
  });
});

describe("search params ↔ filters", () => {
  it("parses valid params and keeps the view", () => {
    const state = parseSearchParams(
      new URLSearchParams("city=Pune&min_price=5000000&bhk=2&property_type=villa&sort=price_asc&page=3&view=map"),
    );
    expect(state).toEqual({
      city: "Pune",
      min_price: 5_000_000,
      bhk: 2,
      property_type: "villa",
      sort: "price_asc",
      page: 3,
      view: "map",
    });
  });

  it("drops invalid values instead of failing the whole page", () => {
    const state = parseSearchParams(new URLSearchParams("bhk=abc&page=-1&sort=cheapest&property_type=castle&city=Noida"));
    expect(state).toEqual({ city: "Noida", view: "list" });
  });

  it("round-trips through the URL", () => {
    const original = { city: "Noida", max_price: 10_000_000, bhk: 3, view: "list" as const };
    expect(parseSearchParams(toSearchParams(original))).toEqual(original);
  });

  it("omits empty values and the default list view", () => {
    expect(toSearchParams({ city: "", bhk: undefined, view: "list" }).toString()).toBe("");
  });
});

describe("image validation", () => {
  const file = (type: string, bytes: number) => new File([new Uint8Array(bytes)], "photo", { type });

  it("accepts JPEG, PNG and WebP up to 5 MB", () => {
    expect(validateImageFile(file("image/jpeg", 5 * 1024 * 1024))).toBeNull();
    expect(validateImageFile(file("image/webp", 10))).toBeNull();
  });

  it("rejects other types and oversized files", () => {
    expect(validateImageFile(file("image/gif", 10))).toMatch(/JPEG, PNG or WebP/);
    expect(validateImageFile(file("image/png", 5 * 1024 * 1024 + 1))).toMatch(/5 MB/);
  });
});

describe("post-login redirect", () => {
  it.each([
    ["/my-bookings", "/my-bookings"],
    ["/listings?city=Pune", "/listings?city=Pune"],
    ["https://evil.com", null],
    ["//evil.com", null],
    [null, null],
  ])("safeNext(%s) is %s", (input, expected) => {
    expect(safeNext(input)).toBe(expected);
  });
});
