import { useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { z } from "zod";

import { LISTING_SORTS, PROPERTY_TYPES, type ListingFilters } from "../types/api";

export type ListingView = "list" | "map";

export interface ListingSearchState extends ListingFilters {
  view: ListingView;
}

// The URL is user-editable, so it's parsed like any other untrusted input: each param is
// validated on its own and a bad value is dropped rather than breaking the whole page.
const positiveInt = z.coerce.number().int().positive();
const nonNegativeInt = z.coerce.number().int().nonnegative();

const PARAM_PARSERS = {
  city: z.string().trim().min(1).max(100),
  min_price: nonNegativeInt,
  max_price: nonNegativeInt,
  bhk: nonNegativeInt.max(20),
  property_type: z.enum(PROPERTY_TYPES),
  sort: z.enum(LISTING_SORTS),
  page: positiveInt,
} as const;

type FilterKey = keyof typeof PARAM_PARSERS;
const FILTER_KEYS = Object.keys(PARAM_PARSERS) as FilterKey[];

export function parseSearchParams(params: URLSearchParams): ListingSearchState {
  const state: Record<string, unknown> = {};
  for (const key of FILTER_KEYS) {
    const raw = params.get(key);
    if (raw === null) continue;
    const parsed = PARAM_PARSERS[key].safeParse(raw);
    if (parsed.success) state[key] = parsed.data;
  }
  const view: ListingView = params.get("view") === "map" ? "map" : "list";
  return { ...(state as ListingFilters), view };
}

export function toSearchParams(state: Partial<ListingSearchState>): URLSearchParams {
  const params = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    const value = state[key];
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  if (state.view === "map") params.set("view", "map");
  return params;
}

/** Search filters, stored in the URL so results are shareable and survive back/forward. */
export function useListingFilters() {
  const [params, setParams] = useSearchParams();
  const state = useMemo(() => parseSearchParams(params), [params]);

  const update = useCallback(
    (changes: Partial<ListingSearchState>) => {
      // Any filter change sends you back to page 1; only explicit page changes keep it.
      const resetPage = !("page" in changes);
      const next = { ...state, ...changes, ...(resetPage ? { page: undefined } : {}) };
      setParams(toSearchParams(next));
    },
    [state, setParams],
  );

  const clear = useCallback(() => setParams(toSearchParams({ view: state.view })), [state.view, setParams]);

  return { state, update, clear };
}
