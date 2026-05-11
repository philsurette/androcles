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

  it("extracts MP3 Playbooks without assuming WAV asset paths", async () => {
    const manifest = manifestWithAudioExtension("mp3");
    const file = await buildPlaybookZip({ manifest });

    const extracted = await extractPlaybookZip(file);

    expect(extracted.assetIndex.has("audio/segments/ANDROCLES/0_1_1.mp3")).toBe(true);
    expect(extracted.manifest.roles[0].lines[0].response.segments[0].audio.path).toBe(
      "audio/segments/ANDROCLES/0_1_1.mp3"
    );
    expect(extracted.audioAssets.find((asset) => asset.path.endsWith(".mp3"))?.blob.type).toBe("audio/mpeg");
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

async function buildPlaybookZip(options: { excludePath?: string; manifest?: typeof manifestFixture } = {}): Promise<Blob> {
  const zip = new JSZip();
  const manifest = options.manifest ?? manifestFixture;
  zip.file("manifest.json", JSON.stringify(manifest));

  for (const audioPath of requiredAudioPaths(manifest)) {
    if (audioPath !== options.excludePath) {
      zip.file(audioPath, "");
    }
  }

  return zip.generateAsync({ type: "blob" });
}

function manifestWithAudioExtension(extension: "mp3" | "wav"): typeof manifestFixture {
  return JSON.parse(JSON.stringify(manifestFixture).replaceAll(".wav", `.${extension}`)) as typeof manifestFixture;
}

function requiredAudioPaths(manifest: typeof manifestFixture): string[] {
  const paths = new Set<string>();
  for (const contextBlock of manifest.context) {
    paths.add(contextBlock.audio.path);
  }
  for (const role of manifest.roles) {
    for (const line of role.lines) {
      paths.add(line.cue.audio.path);
      for (const segment of line.response.segments) {
        paths.add(segment.audio.path);
      }
    }
  }
  return [...paths];
}
