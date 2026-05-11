import { describe, expect, it } from "vitest";
import { validateRecordingPackManifest } from "../../src/specs/validateRecordingPackManifest";

describe("validateRecordingPackManifest", () => {
  it("normalizes a valid role recording pack", () => {
    const pack = validateRecordingPackManifest({
      schema_version: 1,
      package_type: "role_recording_pack",
      play: {
        id: "androcles",
        title: "Androcles and the Lion",
        version: "2026-05-10"
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
          line_id: "0_12_CENTURION",
          block_id: "0.12",
          segment_id: "0_12_1",
          sequence: 1,
          display_text: "Halt!",
          segment_text: "Halt!",
          cue_text: "A bugle is heard.",
          section_id: "part-0",
          section_title: "Act I",
          stage_directions: ["stopping"],
          output_path: "audio/segments/CENTURION/0_12_1.wav"
        }
      ]
    });

    expect(pack.play.id).toBe("androcles");
    expect(pack.role.displayName).toBe("Centurion");
    expect(pack.items[0]).toMatchObject({
      lineId: "0_12_CENTURION",
      segmentId: "0_12_1",
      sectionTitle: "Act I",
      stageDirections: ["stopping"]
    });
  });

  it("rejects unsupported package types", () => {
    expect(() =>
      validateRecordingPackManifest({
        schema_version: 1,
        package_type: "role_recordings",
        play: { id: "androcles", title: "Androcles and the Lion" },
        role: { id: "CENTURION", display_name: "Centurion" },
        recording: { preferred_sample_rate_hz: 48000, preferred_channels: 1, source_format: "wav" },
        items: []
      })
    ).toThrow();
  });
});
