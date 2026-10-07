import { zodResolver } from "@hookform/resolvers/zod";
import { lazy, Suspense } from "react";
import { useForm, useWatch } from "react-hook-form";

import { CITIES } from "../lib/constants";
import { listingSchema, type ListingFormValues } from "../lib/listingSchema";
import { propertyTypeLabel } from "../lib/format";
import { PROPERTY_TYPES, type ListingInput } from "../types/api";
import { Spinner } from "./States";

const LocationPicker = lazy(() => import("./LocationPicker").then((m) => ({ default: m.LocationPicker })));


interface Props {
  defaultValues?: Partial<ListingFormValues>;
  submitLabel: string;
  showStatus?: boolean;
  /** Receives only the fields the user changed (all fields when creating). */
  onSubmit: (values: Partial<ListingInput>) => Promise<void>;
}

const FIELDS_ORDER = Object.keys(listingSchema.shape) as (keyof ListingFormValues)[];

export function ListingForm({ defaultValues, submitLabel, showStatus = false, onSubmit }: Props) {
  const {
    register,
    handleSubmit,
    setValue,
    control,
    reset,
    formState: { errors, isSubmitting, dirtyFields, isDirty },
  } = useForm<ListingFormValues>({
    resolver: zodResolver(listingSchema),
    defaultValues: { property_type: "apartment", status: "active", ...defaultValues },
  });

  const submit = async (values: ListingFormValues) => {
    const changed = defaultValues
      ? Object.fromEntries(FIELDS_ORDER.filter((k) => dirtyFields[k]).map((k) => [k, values[k]]))
      : values;
    await onSubmit(changed);
    reset(values); // the saved values become the new baseline for "changed"
  };

  const field = (name: keyof ListingFormValues) => ({
    id: `listing-${name}`,
    "aria-invalid": errors[name] ? true : undefined,
    "aria-describedby": errors[name] ? `listing-${name}-error` : undefined,
  });
  const error = (name: keyof ListingFormValues) =>
    errors[name] ? (
      <p id={`listing-${name}-error`} className="field-error">
        {errors[name]?.message}
      </p>
    ) : null;

  const [lat, lng] = useWatch({ control, name: ["latitude", "longitude"] });

  return (
    <form onSubmit={handleSubmit(submit)} noValidate className="space-y-5" aria-label="Listing details">
      <div>
        <label htmlFor="listing-title" className="label">Title</label>
        <input className="input" placeholder="Spacious 3 BHK Apartment in Sector 62" {...field("title")} {...register("title")} />
        {error("title")}
      </div>

      <div>
        <label htmlFor="listing-description" className="label">Description</label>
        <textarea rows={4} className="input" {...field("description")} {...register("description")} />
        {error("description")}
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div>
          <label htmlFor="listing-property_type" className="label">Property type</label>
          <select className="input" {...field("property_type")} {...register("property_type")}>
            {PROPERTY_TYPES.map((t) => (
              <option key={t} value={t}>{propertyTypeLabel(t)}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="listing-bhk" className="label">Bedrooms (BHK)</label>
          <input type="number" min={0} className="input" {...field("bhk")} {...register("bhk", { valueAsNumber: true })} />
          {error("bhk")}
        </div>
        <div>
          <label htmlFor="listing-area_sqft" className="label">Area (sq ft)</label>
          <input type="number" min={1} className="input" {...field("area_sqft")} {...register("area_sqft", { valueAsNumber: true })} />
          {error("area_sqft")}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="listing-price" className="label">Price (₹)</label>
          <input type="number" min={1} step={1} className="input" placeholder="8500000" {...field("price")} {...register("price", { valueAsNumber: true })} />
          {error("price")}
        </div>
        {showStatus && (
          <div>
            <label htmlFor="listing-status" className="label">Status</label>
            <select className="input" {...field("status")} {...register("status")}>
              <option value="active">Active (taking visits)</option>
              <option value="sold">Sold</option>
              <option value="inactive">Inactive (hidden from search)</option>
            </select>
          </div>
        )}
      </div>

      <fieldset className="space-y-4">
        <legend className="text-base font-semibold">Location</legend>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="listing-city" className="label">City</label>
            <input className="input" list="listing-city-options" {...field("city")} {...register("city")} />
            <datalist id="listing-city-options">
              {CITIES.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
            {error("city")}
          </div>
          <div>
            <label htmlFor="listing-locality" className="label">Locality</label>
            <input className="input" placeholder="Sector 62" {...field("locality")} {...register("locality")} />
            {error("locality")}
          </div>
        </div>
        <div>
          <label htmlFor="listing-address" className="label">Address</label>
          <input className="input" {...field("address")} {...register("address")} />
          {error("address")}
        </div>
        <div>
          <p className="label">Map pin</p>
          <p className="mb-2 text-xs text-slate-500">Click the map to place the pin, or type coordinates below.</p>
          <Suspense fallback={<div className="grid h-64 place-items-center rounded-lg bg-slate-100"><Spinner /></div>}>
            <LocationPicker
              latitude={Number.isFinite(lat) ? lat : null}
              longitude={Number.isFinite(lng) ? lng : null}
              onPick={(la, lo) => {
                setValue("latitude", la, { shouldDirty: true, shouldValidate: true });
                setValue("longitude", lo, { shouldDirty: true, shouldValidate: true });
              }}
            />
          </Suspense>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="listing-latitude" className="label">Latitude</label>
            <input type="number" step="any" className="input" {...field("latitude")} {...register("latitude", { valueAsNumber: true })} />
            {error("latitude")}
          </div>
          <div>
            <label htmlFor="listing-longitude" className="label">Longitude</label>
            <input type="number" step="any" className="input" {...field("longitude")} {...register("longitude", { valueAsNumber: true })} />
            {error("longitude")}
          </div>
        </div>
      </fieldset>

      <button type="submit" className="btn-primary w-full sm:w-auto" disabled={isSubmitting || (defaultValues !== undefined && !isDirty)}>
        {isSubmitting && <Spinner className="h-4 w-4 border-white/40 border-t-white" />} {submitLabel}
      </button>
    </form>
  );
}
