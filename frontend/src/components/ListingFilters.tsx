import { useState } from "react";

import type { ListingSearchState } from "../hooks/useListingFilters";
import { BHK_OPTIONS, CITIES, PRICE_STEPS } from "../lib/constants";
import { formatPriceShort, propertyTypeLabel } from "../lib/format";
import { LISTING_SORTS, PROPERTY_TYPES, type ListingSort, type PropertyType } from "../types/api";

const SORT_LABELS: Record<ListingSort, string> = {
  newest: "Newest first",
  price_asc: "Price: low to high",
  price_desc: "Price: high to low",
};

interface Props {
  state: ListingSearchState;
  onChange: (changes: Partial<ListingSearchState>) => void;
  onClear: () => void;
}

function toNumber(value: string): number | undefined {
  return value === "" ? undefined : Number(value);
}

/**
 * City is typed freely, so it's applied on Enter/blur rather than on every keystroke.
 * The parent re-keys this component with the URL's city, so the draft resets whenever the
 * URL changes (back button, "Clear filters") without syncing state in an effect.
 */
function CityField({ value, onApply }: { value: string; onApply: (city: string | undefined) => void }) {
  const [draft, setDraft] = useState(value);
  const apply = () => {
    const trimmed = draft.trim();
    if (trimmed !== value) onApply(trimmed || undefined);
  };

  return (
    <div>
      <label htmlFor="filter-city" className="label">
        City
      </label>
      <input
        id="filter-city"
        className="input"
        list="city-options"
        placeholder="Any city"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={apply}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            apply();
          }
        }}
      />
      <datalist id="city-options">
        {CITIES.map((c) => (
          <option key={c} value={c} />
        ))}
      </datalist>
    </div>
  );
}

export function ListingFilters({ state, onChange, onClear }: Props) {
  const priceError =
    state.min_price !== undefined && state.max_price !== undefined && state.min_price > state.max_price;

  return (
    <form onSubmit={(e) => e.preventDefault()} aria-label="Filter listings" className="space-y-5">
      <CityField key={state.city ?? ""} value={state.city ?? ""} onApply={(city) => onChange({ city })} />

      <fieldset>
        <legend className="label">Budget</legend>
        <div className="grid grid-cols-2 gap-2">
          <select
            aria-label="Minimum price"
            className="input"
            value={state.min_price ?? ""}
            onChange={(e) => onChange({ min_price: toNumber(e.target.value) })}
          >
            <option value="">No min</option>
            {PRICE_STEPS.map((p) => (
              <option key={p} value={p}>
                {formatPriceShort(p)}
              </option>
            ))}
          </select>
          <select
            aria-label="Maximum price"
            className="input"
            value={state.max_price ?? ""}
            aria-invalid={priceError}
            onChange={(e) => onChange({ max_price: toNumber(e.target.value) })}
          >
            <option value="">No max</option>
            {PRICE_STEPS.map((p) => (
              <option key={p} value={p}>
                {formatPriceShort(p)}
              </option>
            ))}
          </select>
        </div>
        {priceError && <p className="field-error">Minimum is higher than maximum.</p>}
      </fieldset>

      <fieldset>
        <legend className="label">Bedrooms</legend>
        <div className="flex flex-wrap gap-2">
          {BHK_OPTIONS.map((n) => {
            const active = state.bhk === n;
            return (
              <button
                key={n}
                type="button"
                aria-pressed={active}
                onClick={() => onChange({ bhk: active ? undefined : n })}
                className={`rounded-lg border px-3 py-2 text-sm font-medium transition ${
                  active
                    ? "border-brand-600 bg-brand-600 text-white"
                    : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                }`}
              >
                {n} BHK
              </button>
            );
          })}
        </div>
      </fieldset>

      <div>
        <label htmlFor="filter-type" className="label">
          Property type
        </label>
        <select
          id="filter-type"
          className="input"
          value={state.property_type ?? ""}
          onChange={(e) =>
            onChange({ property_type: (e.target.value || undefined) as PropertyType | undefined })
          }
        >
          <option value="">Any type</option>
          {PROPERTY_TYPES.map((t) => (
            <option key={t} value={t}>
              {propertyTypeLabel(t)}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="filter-sort" className="label">
          Sort by
        </label>
        <select
          id="filter-sort"
          className="input"
          value={state.sort ?? "newest"}
          onChange={(e) => onChange({ sort: e.target.value as ListingSort })}
        >
          {LISTING_SORTS.map((s) => (
            <option key={s} value={s}>
              {SORT_LABELS[s]}
            </option>
          ))}
        </select>
      </div>

      <button type="button" onClick={onClear} className="btn-secondary w-full">
        Clear filters
      </button>
    </form>
  );
}
