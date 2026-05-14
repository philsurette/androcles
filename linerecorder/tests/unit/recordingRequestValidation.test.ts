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
    expect(request.play.id).toBe("androcles");
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

  it("rejects parser-shaped ids", () => {
    expect(() =>
      validateRecordingRequestManifest({
        schema_version: 1,
        package_type: "recording_request",
        request: {
          id: "androcles-CENTURION-full-2026-05-10",
          kind: "full_role",
          created_at: "2026-05-10T14:00:00Z",
          created_by: "stager"
        },
        play: { id: "androcles", title: "Androcles and the Lion" },
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

const line12Hash = "sha256:0000000000000000000000000000000000000000000000000000000000000012";
const segment12Hash = "sha256:0000000000000000000000000000000000000000000000000000000000001012";
