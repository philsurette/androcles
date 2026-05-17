import { describe, expect, it, vi } from "vitest";
import { validateRecordingRequestManifest } from "../../src/specs/validateRecordingRequestManifest";

describe("validateRecordingRequestManifest", () => {
  it("normalizes a valid Recording Request", () => {
    const request = validateRecordingRequestManifest({
      schema_version: 1,
      format_version: "1.0.0",
      package_type: "recording_request",
      request: {
        id: "androcles-CENTURION-full-2026-05-10",
        kind: "full_role",
        created_at: "2026-05-10T14:00:00Z",
        created_by: "stager",
        production_version: "1@k9f4p2x8m1qd",
        notes: "Initial role recording"
      },
      play: {
        id: "androcles",
        title: "Androcles and the Lion",
        version: "2026-05-10"
      },
      production: {
        source: "published",
        version: "1@k9f4p2x8m1qd",
        sequence: 1,
        publication_id: "k9f4p2x8m1qd",
        published_at: "2026-05-10T13:00:00Z"
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
          line_content_hash: line12Hash,
          segment_content_hash: segment12Hash,
          sequence: 1,
          display_text: "Halt!",
          segment_text: "Halt!",
          cue_text: "A bugle is heard.",
          cue_speaker: "_NARRATOR",
          previous_text: "Stand back there.",
          previous_speaker: "FERROVIUS",
          next_text: "Who goes there?",
          next_speaker: "ANDROCLES",
          section_id: "part-0",
          section_title: "Act I",
          stage_directions: ["stopping"],
          blocking: [
            {
              id: "I-12:b1",
              targets: ["CENTURION"],
              text: "checks the gate",
              placement: "inline"
            },
            {
              id: "I-12:b2",
              targets: ["CENTURION"],
              text: "crosses to the gate",
              placement: "before"
            }
          ],
          reason: "initial_recording",
          output_path: "audio/segments/CENTURION/0_12_1.wav"
        }
      ]
    });

    expect(request.request.kind).toBe("full_role");
    expect(request.request.productionVersion).toBe("1@k9f4p2x8m1qd");
    expect(request.packageType).toBe("recording_request");
    expect(request.play.id).toBe("androcles");
    expect(request.production).toMatchObject({
      source: "published",
      version: "1@k9f4p2x8m1qd",
      publicationId: "k9f4p2x8m1qd"
    });
    expect(request.role.displayName).toBe("Centurion");
    expect(request.items[0]).toMatchObject({
      id: "I-12:s1",
      lineId: "I-12",
      segmentId: "0_12_1",
      lineContentHash: line12Hash,
      segmentContentHash: segment12Hash,
      cueSpeaker: "_NARRATOR",
      previousSpeaker: "FERROVIUS",
      nextSpeaker: "ANDROCLES",
      sectionTitle: "Act I",
      reason: "initial_recording",
      stageDirections: ["stopping"],
      blocking: [
        {
          id: "I-12:b1",
          targets: ["CENTURION"],
          text: "checks the gate",
          placement: "inline"
        },
        {
          id: "I-12:b2",
          targets: ["CENTURION"],
          text: "crosses to the gate",
          placement: "before"
        }
      ]
    });
  });

  it("accepts a newer patch format without warning", () => {
    const manifest = recordingRequestManifestFixture();
    manifest.format_version = "1.0.1";
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);

    expect(validateRecordingRequestManifest(manifest).request.kind).toBe("full_role");
    expect(warn).not.toHaveBeenCalled();

    warn.mockRestore();
  });

  it("accepts a newer minor format with a warning", () => {
    const manifest = recordingRequestManifestFixture();
    manifest.format_version = "1.1.0";
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);

    expect(validateRecordingRequestManifest(manifest).request.kind).toBe("full_role");
    expect(warn).toHaveBeenCalledWith(
      "recording_request format version 1.1.0 is newer than supported 1.0.0; newer fields may be ignored."
    );

    warn.mockRestore();
  });

  it("rejects a newer major format", () => {
    const manifest = recordingRequestManifestFixture();
    manifest.format_version = "2.0.0";

    expect(() => validateRecordingRequestManifest(manifest)).toThrow(
      "Unsupported recording_request format version 2.0.0; supported version is 1.0.0"
    );
  });

  it("rejects a missing format version", () => {
    const manifest = recordingRequestManifestFixture() as Partial<ReturnType<typeof recordingRequestManifestFixture>>;
    delete manifest.format_version;

    expect(() => validateRecordingRequestManifest(manifest)).toThrow("recording_request package is missing format_version");
  });

  it("rejects unsupported package types", () => {
    expect(() =>
      validateRecordingRequestManifest({
        schema_version: 1,
        format_version: "1.0.0",
        package_type: "role_recordings",
        request: {
          id: "androcles-CENTURION-full-2026-05-10",
          kind: "full_role",
          created_at: "2026-05-10T14:00:00Z",
          created_by: "stager"
        },
        play: { id: "androcles", title: "Androcles and the Lion" },
        production: { source: "working" },
        role: { id: "CENTURION", display_name: "Centurion" },
        recording: { preferred_sample_rate_hz: 48000, preferred_channels: 1, source_format: "wav" },
        items: []
      })
    ).toThrow();
  });

  it("rejects parser-shaped ids", () => {
    expect(() =>
      validateRecordingRequestManifest({
        schema_version: 1,
        format_version: "1.0.0",
        package_type: "recording_request",
        request: {
          id: "androcles-CENTURION-full-2026-05-10",
          kind: "full_role",
          created_at: "2026-05-10T14:00:00Z",
          created_by: "stager"
        },
        play: { id: "androcles", title: "Androcles and the Lion" },
        production: { source: "working" },
        role: { id: "CENTURION", display_name: "Centurion" },
        recording: { preferred_sample_rate_hz: 48000, preferred_channels: 1, source_format: "wav" },
        items: [
          {
            id: "0_12_1",
            line_id: "0_12_CENTURION",
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
      })
    ).toThrow("Expected a production id");
  });
});

function recordingRequestManifestFixture() {
  return {
    schema_version: 1,
    format_version: "1.0.0",
    package_type: "recording_request" as const,
    request: {
      id: "androcles-CENTURION-full-2026-05-10",
      kind: "full_role" as const,
      created_at: "2026-05-10T14:00:00Z",
      created_by: "stager",
      notes: "Initial role recording"
    },
    play: {
      id: "androcles",
      title: "Androcles and the Lion",
      version: "2026-05-10"
    },
    production: {
      source: "published" as const,
      version: "1@k9f4p2x8m1qd",
      sequence: 1,
      publication_id: "k9f4p2x8m1qd",
      published_at: "2026-05-10T13:00:00Z"
    },
    role: {
      id: "CENTURION",
      display_name: "Centurion"
    },
    recording: {
      preferred_sample_rate_hz: 48000,
      preferred_channels: 1,
      source_format: "wav" as const
    },
    items: []
  };
}

const line12Hash = "sha256:0000000000000000000000000000000000000000000000000000000000000012";
const segment12Hash = "sha256:0000000000000000000000000000000000000000000000000000000000001012";
