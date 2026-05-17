import JSZip from "jszip";
import { describe, expect, it } from "vitest";
import { importRecordingRequest, RecordingRequestImportError } from "../../src/package/importRecordingRequest";

describe("importRecordingRequest", () => {
  it("loads and validates manifest.json from a zip file", async () => {
    const request = await importRecordingRequest(await zipFileWithManifest(manifestFixture()));

    expect(request.request.id).toBe("androcles-CENTURION-full-2026-05-10");
    expect(request.items[0].id).toBe("I-12:s1");
    expect(request.items[0].segmentId).toBe("0_12_1");
  });

  it("rejects zips without a manifest", async () => {
    const zip = new JSZip();
    const blob = await zip.generateAsync({ type: "blob" });
    const file = new File([blob], "bad.recording-request.zip", { type: "application/zip" });

    await expect(importRecordingRequest(file)).rejects.toThrow(RecordingRequestImportError);
  });
});

async function zipFileWithManifest(manifest: unknown): Promise<File> {
  const zip = new JSZip();
  zip.file("manifest.json", JSON.stringify(manifest));
  const blob = await zip.generateAsync({ type: "blob" });
  return new File([blob], "CENTURION.recording-request.zip", { type: "application/zip" });
}

function manifestFixture() {
  return {
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
    production: { source: "working" },
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
        line_content_hash: line12Hash,
        segment_content_hash: segment12Hash,
        sequence: 1,
        display_text: "Halt!",
        segment_text: "Halt!",
        output_path: "audio/segments/CENTURION/0_12_1.wav"
      }
    ]
  };
}

const line12Hash = "sha256:0000000000000000000000000000000000000000000000000000000000000012";
const segment12Hash = "sha256:0000000000000000000000000000000000000000000000000000000000001012";
