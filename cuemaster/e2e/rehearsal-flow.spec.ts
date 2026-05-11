import { expect, test } from "@playwright/test";
import { buildMinimalPlaybookZip } from "./playbookFixture";

test("resumes the last role and line after reload", async ({ page }) => {
  await page.goto("/");

  await page.locator('input[type="file"]').setInputFiles({
    name: "androcles-minimal.playbook.zip",
    mimeType: "application/zip",
    buffer: await buildMinimalPlaybookZip()
  });

  await page.getByRole("button", { name: "Open" }).click();
  await page
    .getByRole("listitem")
    .filter({ hasText: "ANDROCLES" })
    .getByRole("button", { name: "Select" })
    .click();

  await expect(page.getByText("Line 1 of 2")).toBeVisible();
  await expect(page.getByText("PROLOGUE")).toBeVisible();

  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByText("Line 2 of 2")).toBeVisible();
  await expect(page.getByText("You are always talking nonsense.")).toBeVisible();

  await page.reload();
  await page.getByRole("button", { name: "Open" }).click();

  await expect(page.getByText("Androcles and the Lion / ANDROCLES")).toBeVisible();
  await expect(page.getByText("Line 2 of 2")).toBeVisible();
  await expect(page.getByText("You are always talking nonsense.")).toBeVisible();
});
