import { expect, test } from "@playwright/test";

test("loads the Cuemaster shell", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Cuemaster")).toBeVisible();
});
