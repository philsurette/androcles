import { describe, expect, it } from "vitest";
import type { Playbook } from "../../src/domain/playbook";
import type { Role } from "../../src/domain/role";
import { sectionOptionsForRole } from "../../src/rehearsal/sectionOptions";

describe("sectionOptionsForRole", () => {
  it("returns explicit sections that contain lines for the selected role", () => {
    const role = roleWithLines([
      { id: "line-one", partId: 0 },
      { id: "line-two", partId: 0 },
      { id: "line-three", partId: 2 }
    ]);

    expect(sectionOptionsForRole(playbook(), role)).toEqual([
      { id: "part-0", partId: 0, title: "PROLOGUE", startLineId: "line-one", lineCount: 2 },
      { id: "part-2", partId: 2, title: "ACT II", startLineId: "line-three", lineCount: 1 }
    ]);
  });

  it("falls back to generic section labels for older Playbooks", () => {
    expect(sectionOptionsForRole({ ...playbook(), sections: [] }, roleWithLines([{ id: "line-one", partId: 1 }]))).toEqual([
      { id: "part-1", partId: 1, title: "Part 2", startLineId: "line-one", lineCount: 1 }
    ]);
  });
});

function playbook(): Playbook {
  return {
    id: "androcles",
    title: "Androcles and the Lion",
    authors: ["George Bernard Shaw"],
    production: { source: "working" },
    schemaVersion: 1,
    sections: [
      { id: "part-0", partId: 0, blockId: "0.0", title: "PROLOGUE", ordinal: 0 },
      { id: "part-1", partId: 1, blockId: "1.0", title: "ACT I", ordinal: 1 },
      { id: "part-2", partId: 2, blockId: "2.0", title: "ACT II", ordinal: 2 }
    ],
    context: [],
    roles: []
  };
}

function roleWithLines(lines: Array<{ id: string; partId: number | null }>): Role {
  return {
    id: "MEGAERA",
    displayName: "MEGAERA",
    reader: "Anonymous",
    parts: lines.map((line) => line.partId),
    lines: lines.map((line) => ({
      id: line.id,
      partId: line.partId,
      blockId: "0.1",
      role: "MEGAERA",
      speaker: "MEGAERA",
      contentHash: "sha256:0000000000000000000000000000000000000000000000000000000000000001",
      cue: {
        speaker: "_NARRATOR",
        text: "Cue.",
        audioPath: "audio/cue.wav",
        durationMs: 1000
      },
      responseText: line.id,
      responseSegments: [],
      directions: [],
      previousRoles: []
    }))
  };
}
