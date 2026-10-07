/** Cities with seeded listings; offered as suggestions, but any city can be typed. */
export const CITIES = [
  "Bengaluru",
  "Delhi",
  "Greater Noida",
  "Gurugram",
  "Mumbai",
  "Noida",
  "Pune",
] as const;

export interface BudgetOption {
  label: string;
  min?: number;
  max?: number;
}

export const BUDGETS: readonly BudgetOption[] = [
  { label: "Under ₹50 L", max: 5_000_000 },
  { label: "₹50 L – ₹1 Cr", min: 5_000_000, max: 10_000_000 },
  { label: "₹1 Cr – ₹2 Cr", min: 10_000_000, max: 20_000_000 },
  { label: "₹2 Cr – ₹5 Cr", min: 20_000_000, max: 50_000_000 },
  { label: "Above ₹5 Cr", min: 50_000_000 },
];

export const PRICE_STEPS = [
  2_500_000, 5_000_000, 7_500_000, 10_000_000, 15_000_000, 20_000_000, 30_000_000,
  50_000_000, 100_000_000,
] as const;

export const BHK_OPTIONS = [1, 2, 3, 4, 5] as const;

export const DEMO_ACCOUNTS = {
  buyer: { email: "buyer@demo.com", password: "Demo@1234" },
  agent: { email: "agent@demo.com", password: "Demo@1234" },
} as const;
