import { describe, expect, it } from "vitest";
import { normalizePlaybook } from "../../src/playbook/normalizePlaybook";
import type { PlaybookManifest } from "../../src/specs/playbookManifest";

describe("normalizePlaybook", () => {
  it("keeps narrator context separate from selectable roles", () => {
    const manifest: PlaybookManifest = {
      schema_version: 1,
      play: { id: "androcles", title: "Androcles and the Lion", authors: ["George Bernard Shaw"] },
      reading: { type: "solo", build_type: "custom" },
      sections: [{ id: "part-0", part_id: 0, block_id: "0.0", title: "Prologue", ordinal: 0 }],
      context: [
        {
          id: "0_0_1",
          part_id: 0,
          block_id: "0.0",
          kind: "heading",
          speaker: "_NARRATOR",
          text: "Prologue",
          audio: { path: "audio/segments/_NARRATOR/0_0_1.wav", duration_ms: 1000, required: true }
        }
      ],
      roles: [],
      assets: []
    };

    const playbook = normalizePlaybook(manifest);

    expect(playbook.context[0].speaker).toBe("_NARRATOR");
    expect(playbook.sections[0].title).toBe("Prologue");
    expect(playbook.roles).toEqual([]);
  });

  it("preserves line stage directions", () => {
    const manifest: PlaybookManifest = {
      schema_version: 1,
      play: { id: "androcles", title: "Androcles and the Lion", authors: ["George Bernard Shaw"] },
      reading: { type: "solo", build_type: "custom" },
      sections: [{ id: "part-0", part_id: 0, block_id: "0.0", title: "Prologue", ordinal: 0 }],
      context: [],
      roles: [
        {
          id: "MEGAERA",
          display_name: "MEGAERA",
          reader: "Reader",
          meta: false,
          parts: [0],
          lines: [
            {
              id: "0_1_MEGAERA",
              part_id: 0,
              block_id: "0.1",
              role: "MEGAERA",
              speaker: "MEGAERA",
              cue: {
                speaker: "_NARRATOR",
                text: "A forest.",
                audio: { path: "audio/segments/_NARRATOR/0_0_1.wav", duration_ms: 1000, required: true }
              },
              response: {
                text: "I won't go another step.",
                segments: [
                  {
                    id: "0_1_1",
                    owners: ["MEGAERA"],
                    text: "I won't go another step.",
                    audio: { path: "audio/segments/MEGAERA/0_1_1.wav", duration_ms: 1200, required: true }
                  }
                ]
              },
              directions: [{ segment_id: "0_1_1", text: "Sits down.", placement: "inline" }],
              previous_roles: ["_NARRATOR"]
            }
          ]
        }
      ],
      assets: []
    };

    expect(normalizePlaybook(manifest).roles[0].lines[0].directions).toEqual([
      { segmentId: "0_1_1", text: "Sits down.", placement: "inline" }
    ]);
  });
});
