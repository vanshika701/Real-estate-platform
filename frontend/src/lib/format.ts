import type { PropertyType } from "../types/api";

const LAKH = 100_000;
const CRORE = 10_000_000;

function trim(value: number): string {
  return value.toFixed(2).replace(/\.?0+$/, "");
}

/** Compact Indian price: ₹42 L, ₹1.25 Cr. */
export function formatPriceShort(price: number): string {
  if (price >= CRORE) return `₹${trim(price / CRORE)} Cr`;
  if (price >= LAKH) return `₹${trim(price / LAKH)} L`;
  return `₹${price.toLocaleString("en-IN")}`;
}

/** Full Indian-grouped price: ₹1,25,00,000. */
export function formatPriceFull(price: number): string {
  return `₹${price.toLocaleString("en-IN")}`;
}

export function formatArea(sqft: number): string {
  return `${sqft.toLocaleString("en-IN")} sq ft`;
}

const PROPERTY_TYPE_LABELS: Record<PropertyType, string> = {
  apartment: "Apartment",
  villa: "Villa",
  plot: "Plot",
  independent_house: "Independent house",
};

export function propertyTypeLabel(type: PropertyType): string {
  return PROPERTY_TYPE_LABELS[type];
}

/** "3 BHK", or nothing for plots, which have no bedrooms. */
export function bhkLabel(bhk: number): string | null {
  return bhk > 0 ? `${bhk} BHK` : null;
}
