import { expect, type Page, test } from "@playwright/test";
import { buildMinimalPlaybookZip } from "./playbookFixture";

test("resumes the last role and line after reload", async ({ page }) => {
  await openAndroclesRole(page);

  await expect(page.locator("p.line-position").getByText("I-1")).toBeVisible();
  await expect(page.getByLabel("Cue", { exact: true }).getByText("PROLOGUE")).toBeVisible();

  await page.getByRole("button", { name: /go to next line/i }).click();
  await expect(page.locator("p.line-position").getByText("I-3")).toBeVisible();

  await page.reload();
  await page.getByRole("button", { name: "Rehearse!" }).click();

  await expect(page.getByText("Androcles and the Lion")).toBeVisible();
  await expect(page.getByText("ANDROCLES")).toBeVisible();
  await expect(page.locator("p.line-position").getByText("I-3")).toBeVisible();
});

test("repeat cue does not advance the current line", async ({ page }) => {
  await openAndroclesRole(page);

  await expect(page.locator("p.line-position").getByText("I-1")).toBeVisible();
  await page.getByRole("button", { name: /start cue/i }).click();
  await expect(page.locator("p.line-position").getByText("I-1")).toBeVisible();
  await page.getByRole("button", { name: /repeat cue/i }).click();
  await expect(page.locator("p.line-position").getByText("I-1")).toBeVisible();
});

test("hear my line does not advance the current line", async ({ page }) => {
  await openAndroclesRole(page);

  await expect(page.locator("p.line-position").getByText("I-1")).toBeVisible();
  await page.getByRole("button", { name: /hear your line/i }).click();
  await expect(page.locator("p.line-position").getByText("I-1")).toBeVisible();
});

test("show lines by default reveals each line while navigating", async ({ page }) => {
  await openAndroclesRole(page);

  await expect(page.getByText("Line hidden")).toBeVisible();
  await page.getByRole("button", { name: "Show lines." }).click();
  await expect(page.getByText("Not bloody likely.")).toBeVisible();

  await page.getByRole("button", { name: /go to next line/i }).click();
  await expect(page.getByText("It is the best sense I can make of it.")).toBeVisible();
});

test("back returns to the previous line", async ({ page }) => {
  await openAndroclesRole(page);

  await page.getByRole("button", { name: /go to next line/i }).click();
  await expect(page.locator("p.line-position").getByText("I-3")).toBeVisible();

  await page.getByRole("button", { name: /go to previous line/i }).click();
  await expect(page.locator("p.line-position").getByText("I-1")).toBeVisible();
  await expect(page.getByLabel("Cue", { exact: true }).getByText("PROLOGUE")).toBeVisible();
});

test("does not show the removed bookmarks utility tab", async ({ page }) => {
  await openAndroclesRole(page);

  await expect(page.getByRole("button", { name: "Timing" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Options" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Bookmarks" })).toHaveCount(0);
});

test("filters outline to bookmarked lines only in browse mode", async ({ page }) => {
  await openAndroclesRole(page);

  await page.getByRole("button", { name: "Show bookmarked lines only" }).click();
  await expect(page.getByText("No matching bookmarked cues.")).toBeVisible();
});

test("filters outline to slow timing lines only", async ({ page }) => {
  await openAndroclesRole(page);

  await page.getByRole("button", { name: "Show slow timing lines only" }).click();
  await expect(page.getByText("No matching slow cues.")).toBeVisible();
});

async function openAndroclesRole(page: Page) {
  await page.goto("/");

  await page.locator('input[type="file"]').setInputFiles({
    name: "androcles-minimal.playbook.zip",
    mimeType: "application/zip",
    buffer: await buildMinimalPlaybookZip()
  });

  await page.getByRole("button", { name: "Rehearse!" }).click();
  await page
    .getByRole("listitem")
    .filter({ hasText: "ANDROCLES" })
    .getByRole("button", { name: "Select" })
    .click();
}
