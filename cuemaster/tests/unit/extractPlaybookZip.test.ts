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

  it("extracts staging JSON assets referenced by the diagram bundle manifest", async () => {
    const manifest = {
      ...manifestFixture,
      format_version: "1.1.0",
      staging: {
        included: true,
        format: "quince.blocking.diagram_bundle",
        format_version: "1.0.0",
        manifest_path: "staging/diagram_manifest.json"
      }
    } as typeof manifestFixture;
    const file = await buildPlaybookZip({ manifest, staging: true });

    const extracted = await extractPlaybookZip(file);

    expect(extracted.jsonAssets.map((asset) => asset.path).sort()).toEqual([
      "staging/checkpoints/scene-start.json",
      "staging/deltas/scene-b1.json",
      "staging/diagram_manifest.json",
      "staging/icons.svg"
    ]);
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

  it("reports manifest validation paths for production id errors", async () => {
    const invalidManifest = structuredClone(manifestFixture);
    invalidManifest.context[0].id = "0_0_1";

    const zip = new JSZip();
    zip.file("manifest.json", JSON.stringify(invalidManifest));

    await expect(extractPlaybookZip(await zip.generateAsync({ type: "blob" }))).rejects.toThrow(
      "context.0.id: Expected a production id"
    );
  });

  it("reports missing required audio assets before import succeeds", async () => {
    const file = await buildPlaybookZip({ excludePath: "audio/segments/ANDROCLES/0_1_1.wav" });

    await expect(extractPlaybookZip(file)).rejects.toThrow(
      "Playbook zip is missing required audio asset: audio/segments/ANDROCLES/0_1_1.wav"
    );
  });
});

async function buildPlaybookZip(options: {
  excludePath?: string;
  manifest?: typeof manifestFixture;
  staging?: boolean;
} = {}): Promise<Blob> {
  const zip = new JSZip();
  const manifest = options.manifest ?? manifestFixture;
  zip.file("manifest.json", JSON.stringify(manifest));
  if (options.staging) {
    zip.file("staging/diagram_manifest.json", JSON.stringify(stagingManifest()));
    zip.file("staging/checkpoints/scene-start.json", "{}");
    zip.file("staging/deltas/scene-b1.json", "{}");
    zip.file("staging/icons.svg", '<defs><symbol id="stage-icon-table" viewBox="0 0 24 24"></symbol></defs>');
  }

  for (const audioPath of requiredAudioPaths(manifest)) {
    if (audioPath !== options.excludePath) {
      zip.file(audioPath, "");
    }
  }

  return zip.generateAsync({ type: "blob" });
}

function stagingManifest() {
  return {
    format: "quince.blocking.diagram_bundle",
    format_version: "1.0.0",
    icon_library: {
      format: "svg-symbols",
      path: "staging/icons.svg"
    },
    checkpoints: [{ id: "scene:start", scene_id: "1", path: "staging/checkpoints/scene-start.json" }],
    deltas: [
      {
        id: "scene:1@b1",
        scene_id: "1",
        beat_id: "b1",
        production_anchor: "1-1",
        from_checkpoint: "scene:start",
        path: "staging/deltas/scene-b1.json"
      }
    ]
  };
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
