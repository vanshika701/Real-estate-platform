import { expect, test, type Page } from "@playwright/test";

import { bookViaApi, createListingWithSlots, deleteListing, DEMO_AGENT, login, type TestListing } from "./api";

/**
 * The two core journeys, end to end through the real stack:
 *   buyer:  sign up → search → open listing → hold slot → confirm → see it in My Bookings
 *   agent:  log in → see the booking (live) → accept → buyer sees it accepted
 */
test.describe.configure({ mode: "serial" });

const runId = Date.now();
const buyer = {
  name: `E2E Buyer ${runId}`,
  email: `e2e-buyer-${runId}@example.com`,
  password: "Visit2026",
};

let agentToken: string;
let listing: TestListing;

test.beforeAll(async ({ request }) => {
  agentToken = await login(request, DEMO_AGENT.email, DEMO_AGENT.password);
  listing = await createListingWithSlots(request, agentToken);
});

test.afterAll(async ({ request }) => {
  // Deleting the listing also removes its slots and bookings.
  if (listing) await deleteListing(request, agentToken, listing.id);
});

async function loginAsDemoAgent(page: Page) {
  await page.goto("/login");
  await page.getByRole("button", { name: "Try as Agent" }).click();
  await expect(page).toHaveURL(/\/agent\/dashboard$/);
}

test("buyer signs up, searches, books a visit and sees it in My Bookings", async ({ page }) => {
  await test.step("sign up as a buyer", async () => {
    await page.goto("/signup");
    await page.getByLabel("Full name").fill(buyer.name);
    await page.getByLabel("Email").fill(buyer.email);
    await page.getByLabel("Password").fill(buyer.password);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/listings$/);
    await expect(page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "My bookings" })).toBeVisible();
  });

  await test.step("search by city from the home page", async () => {
    await page.goto("/");
    await page.getByLabel("City").fill(listing.city);
    await page.getByRole("button", { name: "Search" }).click();
    await expect(page).toHaveURL(new RegExp(`/listings\\?city=${listing.city}`));
    await expect(page.getByLabel("City")).toHaveValue(listing.city); // filters reflect the URL
  });

  await test.step("open the listing", async () => {
    await page.getByRole("link", { name: new RegExp(listing.title) }).click();
    await expect(page.getByRole("heading", { level: 1, name: listing.title })).toBeVisible();
  });

  await test.step("hold a slot and see the countdown", async () => {
    const times = page.getByRole("tabpanel", { name: "Times" });
    await times.getByRole("button", { name: /11:00 am, available/ }).click();
    await expect(page.getByRole("timer")).toHaveText(/^[45]:\d\d$/);
    await expect(times.getByRole("button", { name: /11:00 am, your hold/ })).toBeVisible();
  });

  await test.step("confirm the booking", async () => {
    await page.getByLabel(/Note for the agent/).fill("E2E: please call on arrival");
    await page.getByRole("button", { name: "Confirm visit" }).click();
    await expect(page.getByText("Visit requested!")).toBeVisible();
  });

  await test.step("see it in My Bookings as pending", async () => {
    await page.getByRole("link", { name: "View my bookings" }).click();
    const booking = page.getByRole("listitem").filter({ hasText: listing.title });
    await expect(booking).toBeVisible();
    await expect(booking.getByText("pending", { exact: true })).toBeVisible();
    await expect(booking.getByText("E2E: please call on arrival")).toBeVisible();
  });
});

test("agent sees the booking and accepts it", async ({ page, browser }) => {
  await loginAsDemoAgent(page);

  const row = page.getByRole("row").filter({ hasText: buyer.name });
  await expect(row).toContainText(listing.title);
  await expect(row.getByText("pending", { exact: true })).toBeVisible();

  await row.getByRole("button", { name: `Accept visit from ${buyer.name}` }).click();
  await expect(page.getByText("Visit accepted")).toBeVisible();

  await page.getByRole("tab", { name: "Accepted" }).click();
  await expect(page.getByRole("row").filter({ hasText: buyer.name }).getByText("accepted", { exact: true })).toBeVisible();

  // The buyer now sees it as accepted.
  const buyerContext = await browser.newContext();
  const buyerPage = await buyerContext.newPage();
  await buyerPage.goto("/login");
  await buyerPage.getByLabel("Email").fill(buyer.email);
  await buyerPage.getByLabel("Password").fill(buyer.password);
  await buyerPage.getByRole("button", { name: "Log in" }).click();
  await buyerPage.getByRole("link", { name: "My bookings" }).first().click();
  const booking = buyerPage.getByRole("listitem").filter({ hasText: listing.title });
  await expect(booking.getByText("accepted", { exact: true })).toBeVisible();
  await buyerContext.close();
});

test("agent dashboard updates live when a new booking arrives", async ({ page, request }) => {
  await loginAsDemoAgent(page);
  await expect(page.getByText("Live", { exact: true })).toBeVisible();
  const pending = page.getByText("Pending requests").locator("..").getByRole("paragraph").nth(1);
  const before = Number(await pending.textContent());

  // The buyer books another slot while the agent watches.
  const buyerToken = await login(request, buyer.email, buyer.password);
  await bookViaApi(request, buyerToken, listing.id);

  await expect(page.getByRole("status").filter({ hasText: "New visit request" })).toContainText(buyer.name);
  await expect(pending).toHaveText(String(before + 1));
});
