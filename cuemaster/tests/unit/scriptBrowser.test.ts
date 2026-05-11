import { describe, expect, it } from "vitest";
import type { Line } from "../../src/domain/line";
import { scriptBrowserSections } from "../../src/rehearsal/scriptBrowser";

describe("scriptBrowserSections", () => {
  it("groups role lines by part", () => {
    expect(scriptBrowserSections([line("one", 0), line("two", 0), line("three", 1)])).toMatchObject([
      { id: "part-0", title: "Part 1", lines: [{ id: "one" }, { id: "two" }] },
      { id: "part-1", title: "Part 2", lines: [{ id: "three" }] }
    ]);
  });

  it("uses play section for lines without a part", () => {
    expect(scriptBrowserSections([line("one", null)])).toMatchObject([
      { id: "play", title: "Play", lines: [{ id: "one" }] }
    ]);
  });
});

function line(id: string, partId: number | null): Line {
  return {
    id,
    partId,
    blockId: "0.1",
    role: "MEGAERA",
    speaker: "MEGAERA",
    cue: {
      speaker: "_NARRATOR",
      text: "Cue.",
      audioPath: "cue.wav",
      durationMs: 1000
    },
    responseText: id,
    responseSegments: [],
    directions: [],
    previousRoles: []
  };
}
