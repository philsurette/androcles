import { expect, test } from "@playwright/test";

test("shows the LineRecorder library", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "LineRecorder" })).toBeVisible();
  await expect(page.getByText("No Recording Requests imported")).toBeVisible();
});
