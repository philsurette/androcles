import { describe, expect, it } from "vitest";
import { validateRecordingRequestManifest } from "../../src/specs/validateRecordingRequestManifest";

describe("validateRecordingRequestManifest", () => {
  it("normalizes a valid Recording Request", () => {
    const request = validateRecordingRequestManifest({
      schema_version: 1,
      package_type: "recording_request",
      request: {
        id: "androcles-CENTURION-full-2026-05-10",
        kind: "full_role",
        created_at: "2026-05-10T14:00:00Z",
        created_by: "stager",
        notes: "Initial role recording"
      },
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
          cue_speaker: "_NARRATOR",
          previous_text: "Stand back there.",
          previous_speaker: "FERROVIUS",
          next_text: "Who goes there?",
          next_speaker: "ANDROCLES",
          section_id: "part-0",
          section_title: "Act I",
          stage_directions: ["stopping"],
          reason: "initial_recording",
          output_path: "audio/segments/CENTURION/0_12_1.wav"
        }
      ]
    });

    expect(request.request.kind).toBe("full_role");
    expect(request.play.id).toBe("androcles");
    expect(request.role.displayName).toBe("Centurion");
    expect(request.items[0]).toMatchObject({
      lineId: "0_12_CENTURION",
      segmentId: "0_12_1",
      cueSpeaker: "_NARRATOR",
      previousSpeaker: "FERROVIUS",
      nextSpeaker: "ANDROCLES",
      sectionTitle: "Act I",
      reason: "initial_recording",
      stageDirections: ["stopping"]
    });
  });

  it("rejects unsupported package types", () => {
    expect(() =>
      validateRecordingRequestManifest({
        schema_version: 1,
        package_type: "role_recordings",
        request: {
          id: "androcles-CENTURION-full-2026-05-10",
          kind: "full_role",
          created_at: "2026-05-10T14:00:00Z",
          created_by: "stager"
        },
        play: { id: "androcles", title: "Androcles and the Lion" },
        role: { id: "CENTURION", display_name: "Centurion" },
        recording: { preferred_sample_rate_hz: 48000, preferred_channels: 1, source_format: "wav" },
        items: []
      })
    ).toThrow();
  });
});
