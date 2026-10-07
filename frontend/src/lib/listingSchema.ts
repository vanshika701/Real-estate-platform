import { z } from "zod";

import { PROPERTY_TYPES } from "../types/api";

// Number inputs use valueAsNumber, so an empty field arrives as NaN; give it a friendly message.
const num = (message: string) => z.number({ message }).refine((n) => !Number.isNaN(n), message);

export const listingSchema = z.object({
  title: z.string().trim().min(5, "At least 5 characters").max(200),
  description: z.string().trim().min(10, "At least 10 characters").max(5000),
  city: z.string().trim().min(1, "Enter a city").max(100),
  locality: z.string().trim().min(1, "Enter a locality").max(100),
  address: z.string().trim().min(1, "Enter an address").max(300),
  latitude: num("Enter a latitude").pipe(z.number().min(-90).max(90)),
  longitude: num("Enter a longitude").pipe(z.number().min(-180).max(180)),
  price: num("Enter a price").pipe(z.number().int("Whole rupees only").positive("Must be more than 0")),
  bhk: num("Enter bedrooms (0 for plots)").pipe(z.number().int().min(0).max(20)),
  area_sqft: num("Enter the area").pipe(z.number().int().positive("Must be more than 0")),
  property_type: z.enum(PROPERTY_TYPES),
  status: z.enum(["active", "sold", "inactive"]),
});

export type ListingFormValues = z.infer<typeof listingSchema>;
