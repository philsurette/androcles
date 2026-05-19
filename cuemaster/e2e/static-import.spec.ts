import { expect, test, type Page } from "@playwright/test";
import { buildMinimalPlaybookZip } from "./playbookFixture";

test("imports and keeps a Playbook when served from a nested static path", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("QUINCE CUEMASTER")).toBeVisible();

  await page.locator('input[type="file"]').setInputFiles({
    name: "androcles-minimal.playbook.zip",
    mimeType: "application/zip",
    buffer: await buildMinimalPlaybookZip()
  });

  await expect(page.getByText("Imported Androcles and the Lion")).toBeVisible();
  await expect(page.getByText("Roles: ANDROCLES, MEGAERA")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Androcles and the Lion" })).toBeVisible();
  await expect.poll(() => storedAudioAssetCount(page)).toBeGreaterThan(0);

  await page.reload();

  await expect(page.getByRole("heading", { name: "Androcles and the Lion" })).toBeVisible();
  await page.getByRole("button", { name: "Rehearse" }).click();
  await expect(page.getByRole("option", { name: /ANDROCLES/ })).toBeVisible();
  await expect.poll(() => storedAudioAssetCount(page)).toBeGreaterThan(0);
});

async function storedAudioAssetCount(page: Page): Promise<number> {
  return page.evaluate(
    () =>
      new Promise<number>((resolve, reject) => {
        const request = indexedDB.open("cuemaster");
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
          const db = request.result;
          const transaction = db.transaction("audioAssets", "readonly");
          const countRequest = transaction.objectStore("audioAssets").count();
          countRequest.onerror = () => reject(countRequest.error);
          countRequest.onsuccess = () => {
            const count = countRequest.result;
            db.close();
            resolve(count);
          };
        };
      })
  );
}
