import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";
import { readFile, writeFile } from "node:fs/promises";
import JSZip from "jszip";

test("shows the LineRecorder library", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "LineRecorder" })).toBeVisible();
  await expect(page.getByText("No Recording Requests imported")).toBeVisible();
});

test("exports accepted recordings as a browser download", async ({ page }, testInfo) => {
  const requestPath = testInfo.outputPath("recording-request.zip");
  await writeRecordingRequestZip(requestPath);

  await page.goto("/");
  const fileChooserPromise = page.waitForEvent("filechooser");
  await page.getByText("Import Request").click();
  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles(requestPath);
  await expect(page.getByRole("heading", { name: "Centurion" })).toBeVisible();

  await seedAcceptedTake(page);
  await page.getByRole("button", { name: "Back" }).click();
  await page.getByRole("button", { name: "Open" }).click();
  await expect(page.getByText("1/1", { exact: true })).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export Recordings" }).click();
  const download = await downloadPromise;

  expect(download.suggestedFilename()).toBe("androcles-CENTURION-role-recordings-20260510T140000Z.zip");
  await expect(page.getByRole("status")).toContainText(
    "Exported androcles-CENTURION-role-recordings-20260510T140000Z.zip"
  );

  const downloadPath = testInfo.outputPath(download.suggestedFilename());
  await download.saveAs(downloadPath);
  const zip = await JSZip.loadAsync(await readFile(downloadPath));
  const manifest = JSON.parse(await zip.file("manifest.json")!.async("string"));

  expect(manifest).toMatchObject({
    package_type: "role_recordings",
    complete: true,
    play: {
      id: "androcles"
    },
    role: {
      id: "CENTURION"
    },
    recordings: [
      {
        id: "I-12:s1",
        audio_path: "audio/segments/CENTURION/0_12_1.wav"
      }
    ]
  });
  await expect(zip.file("audio/segments/CENTURION/0_12_1.wav")!.async("string")).resolves.toBe("fake wav");
});

async function writeRecordingRequestZip(path: string): Promise<void> {
  const zip = new JSZip();
  zip.file(
    "manifest.json",
    JSON.stringify(
      {
        schema_version: 1,
        format_version: "1.0.0",
        package_type: "recording_request",
        request: {
          id: "androcles-CENTURION-full-2026-05-10",
          kind: "full_role",
          created_at: "2026-05-10T14:00:00Z",
          created_by: "stager"
        },
        play: {
          id: "androcles",
          title: "Androcles and the Lion"
        },
        role: {
          id: "CENTURION",
          display_name: "Centurion"
        },
        recording: {
          preferred_sample_rate_hz: 48000,
          preferred_channels: 1,
          source_format: "wav"
        },
        items: [
          {
            id: "I-12:s1",
            line_id: "I-12",
            block_id: "0.12",
            segment_id: "0_12_1",
            line_content_hash: "sha256:0000000000000000000000000000000000000000000000000000000000000012",
            segment_content_hash: "sha256:0000000000000000000000000000000000000000000000000000000000001012",
            sequence: 1,
            display_text: "Halt!",
            segment_text: "Halt!",
            output_path: "audio/segments/CENTURION/0_12_1.wav",
            stage_directions: []
          }
        ]
      },
      null,
      2
    )
  );
  await writeFile(path, await zip.generateAsync({ type: "nodebuffer" }));
}

async function seedAcceptedTake(page: Page): Promise<void> {
  await page.evaluate(async () => {
    const db = await new Promise<IDBDatabase>((resolve, reject) => {
      const request = indexedDB.open("linerecorder");
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
    });

    await new Promise<void>((resolve, reject) => {
      const transaction = db.transaction("takes", "readwrite");
      transaction.onerror = () => reject(transaction.error);
      transaction.oncomplete = () => resolve();
      transaction.objectStore("takes").put({
        id: "take-I-12:s1",
        projectId: "androcles-CENTURION-full-2026-05-10",
        segmentId: "I-12:s1",
        status: "accepted",
        recordedAt: "2026-05-11T12:00:00Z",
        durationMs: 1000,
        sampleRateHz: 48000,
        channels: 1,
        inputQuality: {
          peakEnergy: 0.14,
          levelCounts: {
            noSignal: 0,
            tooQuiet: 0,
            good: 10,
            clipping: 0
          }
        },
        blob: new Blob(["fake wav"], { type: "audio/wav" })
      });
    });
    db.close();
  });
}
