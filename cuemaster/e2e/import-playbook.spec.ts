import { expect, test } from "@playwright/test";
import { buildMinimalPlaybookZip } from "./playbookFixture";

test("loads the Cuemaster shell", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Cuemaster")).toBeVisible();
});

test("imports a Playbook and shows actor roles", async ({ page }) => {
  await page.goto("/");

  await page.locator('input[type="file"]').setInputFiles({
    name: "androcles-minimal.playbook.zip",
    mimeType: "application/zip",
    buffer: await buildMinimalPlaybookZip()
  });

  await expect(page.getByText("Imported Androcles and the Lion")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Androcles and the Lion" })).toBeVisible();
  await expect(page.getByText("2 roles: ANDROCLES, MEGAERA")).toBeVisible();

  await page.getByRole("button", { name: "Open" }).click();

  await expect(page.getByText("Choose Role")).toBeVisible();
  await expect(page.getByRole("heading", { name: "ANDROCLES", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "MEGAERA", exact: true })).toBeVisible();
});

test("reports an invalid Playbook zip", async ({ page }) => {
  await page.goto("/");

  await page.locator('input[type="file"]').setInputFiles({
    name: "not-a-playbook.zip",
    mimeType: "application/zip",
    buffer: Buffer.from("not a zip")
  });

  await expect(page.getByRole("alert")).toContainText("Invalid Playbook zip");
});
