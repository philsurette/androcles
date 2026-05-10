import { describe, expect, it } from "vitest";
import { normalizePlaybook } from "../../src/playbook/normalizePlaybook";
import type { PlaybookManifest } from "../../src/specs/playbookManifest";

describe("normalizePlaybook", () => {
  it("keeps narrator context separate from selectable roles", () => {
    const manifest: PlaybookManifest = {
      schema_version: 1,
      play: { id: "androcles", title: "Androcles and the Lion", authors: ["George Bernard Shaw"] },
      reading: { type: "solo", build_type: "custom" },
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
    expect(playbook.roles).toEqual([]);
  });
});
