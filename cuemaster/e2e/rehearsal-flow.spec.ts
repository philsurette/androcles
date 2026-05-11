import { expect, type Page, test } from "@playwright/test";
import { buildMinimalPlaybookZip } from "./playbookFixture";

test("resumes the last role and line after reload", async ({ page }) => {
  await openAndroclesRole(page);

  await expect(page.getByText("Line 1 of 2")).toBeVisible();
  await expect(page.getByLabel("Cue", { exact: true }).getByText("PROLOGUE")).toBeVisible();

  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByText("Line 2 of 2")).toBeVisible();
  await expect(page.getByText("You are always talking nonsense.")).toBeVisible();

  await page.reload();
  await page.getByRole("button", { name: "Open" }).click();

  await expect(page.getByText("Androcles and the Lion / ANDROCLES")).toBeVisible();
  await expect(page.getByText("Line 2 of 2")).toBeVisible();
  await expect(page.getByText("You are always talking nonsense.")).toBeVisible();
});

test("repeat cue does not advance the current line", async ({ page }) => {
  await openAndroclesRole(page);

  await expect(page.getByText("Line 1 of 2")).toBeVisible();
  await page.getByRole("button", { name: /start or repeat cue/i }).click();
  await expect(page.getByText("Line 1 of 2")).toBeVisible();
  await page.getByRole("button", { name: /start or repeat cue/i }).click();
  await expect(page.getByText("Line 1 of 2")).toBeVisible();
});

test("hear my line does not advance the current line", async ({ page }) => {
  await openAndroclesRole(page);

  await expect(page.getByText("Line 1 of 2")).toBeVisible();
  await page.getByRole("button", { name: /hear your line/i }).click();
  await expect(page.getByText("Line 1 of 2")).toBeVisible();
});

test("show lines by default reveals each line while navigating", async ({ page }) => {
  await openAndroclesRole(page);

  await expect(page.getByText("Line hidden")).toBeVisible();
  await page.getByLabel("Show lines by default").check();
  await expect(page.getByText("Not bloody likely.")).toBeVisible();
  await expect(page.getByRole("button", { name: /hide your line/i })).toBeVisible();

  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByText("It is the best sense I can make of it.")).toBeVisible();
  await expect(page.getByRole("button", { name: /hide your line/i })).toBeVisible();
});

test("back returns to the previous line", async ({ page }) => {
  await openAndroclesRole(page);

  await page.getByRole("button", { name: "Next" }).click();
  await expect(page.getByText("Line 2 of 2")).toBeVisible();

  await page.getByRole("button", { name: /go to previous line/i }).click();
  await expect(page.getByText("Line 1 of 2")).toBeVisible();
  await expect(page.getByLabel("Cue", { exact: true }).getByText("PROLOGUE")).toBeVisible();
});

async function openAndroclesRole(page: Page) {
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
}
