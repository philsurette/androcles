import JSZip from "jszip";
import { describe, expect, it } from "vitest";
import { extractPlaybookZip } from "../../src/playbook/extractPlaybookZip";
import { PlaybookImportError } from "../../src/playbook/playbookImportError";
import manifestFixture from "../fixtures/minimal-playbook/manifest.json";

describe("extractPlaybookZip", () => {
  it("extracts a valid Playbook manifest and indexes audio assets", async () => {
    const file = await buildPlaybookZip();

    const extracted = await extractPlaybookZip(file);

    expect(extracted.manifest.play.id).toBe("androcles-minimal");
    expect(extracted.assetIndex.has("audio/segments/ANDROCLES/0_1_1.wav")).toBe(true);
  });

  it("reports an invalid zip with a friendly import error", async () => {
    await expect(extractPlaybookZip(new Blob(["not a zip"]))).rejects.toThrow(PlaybookImportError);
    await expect(extractPlaybookZip(new Blob(["not a zip"]))).rejects.toThrow("Invalid Playbook zip");
  });

  it("reports a missing manifest with a friendly import error", async () => {
    const zip = new JSZip();
    zip.file("audio/segments/ANDROCLES/0_1_1.wav", "");

    await expect(extractPlaybookZip(await zip.generateAsync({ type: "blob" }))).rejects.toThrow(
      "Playbook zip is missing manifest.json"
    );
  });

  it("reports invalid manifest JSON with a friendly import error", async () => {
    const zip = new JSZip();
    zip.file("manifest.json", "{");

    await expect(extractPlaybookZip(await zip.generateAsync({ type: "blob" }))).rejects.toThrow(
      "Playbook manifest is not valid JSON"
    );
  });

  it("reports schema-invalid manifests with a friendly import error", async () => {
    const invalidManifest = structuredClone(manifestFixture);
    delete (invalidManifest.play as Partial<typeof invalidManifest.play>).title;

    const zip = new JSZip();
    zip.file("manifest.json", JSON.stringify(invalidManifest));

    await expect(extractPlaybookZip(await zip.generateAsync({ type: "blob" }))).rejects.toThrow(
      "Playbook manifest is invalid"
    );
  });

  it("reports missing required audio assets before import succeeds", async () => {
    const file = await buildPlaybookZip({ excludePath: "audio/segments/ANDROCLES/0_1_1.wav" });

    await expect(extractPlaybookZip(file)).rejects.toThrow(
      "Playbook zip is missing required audio asset: audio/segments/ANDROCLES/0_1_1.wav"
    );
  });
});

async function buildPlaybookZip(options: { excludePath?: string } = {}): Promise<Blob> {
  const zip = new JSZip();
  zip.file("manifest.json", JSON.stringify(manifestFixture));

  const audioPaths = [
    "audio/segments/_NARRATOR/0_0_1.wav",
    "audio/segments/ANDROCLES/0_1_1.wav",
    "audio/segments/ANDROCLES/0_3_1.wav",
    "audio/segments/MEGAERA/0_2_1.wav"
  ];

  for (const audioPath of audioPaths) {
    if (audioPath !== options.excludePath) {
      zip.file(audioPath, "");
    }
  }

  return zip.generateAsync({ type: "blob" });
}
