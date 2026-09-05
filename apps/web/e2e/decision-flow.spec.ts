import { expect, test } from "@playwright/test";

test("analyst evaluates, verifies, and audits a payment intent", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Risk command center" })).toBeVisible();
  await page.getByLabel("Password").fill(process.env.DEMO_USER_PASSWORD ?? "");
  await page.getByRole("button", { name: /Enter command center/ }).click();
  await expect(page.getByRole("heading", { name: "Today’s control surface" })).toBeVisible();

  await page.getByRole("button", { name: /Delegation edge/ }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByText("VERIFY", { exact: true })).toBeVisible();
  await expect(page.getByText("DECISION RATIONALE", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Approve intent" }).click();
  await expect(page.getByRole("button", { name: /Create Razorpay test order/ })).toBeVisible();
  await page.getByRole("button", { name: /Create Razorpay test order/ }).click();
  await expect(page.getByText(/Razorpay test order order_demo_/)).toBeVisible();
  await expect(page.getByText(/payment \/ order_created/)).toBeVisible();
});

test("hard policy violation has no execution control", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Password").fill(process.env.DEMO_USER_PASSWORD ?? "");
  await page.getByRole("button", { name: /Enter command center/ }).click();
  await page.getByRole("button", { name: /Mandate violation/ }).click();
  await expect(page.getByText("BLOCK", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /Create Razorpay test order/ })).toHaveCount(0);
});
