import { describe, expect, it } from "vitest";
import { rehearsalCommands } from "../../src/rehearsal/rehearsalCommand";

describe("rehearsalCommands", () => {
  it("defines input-independent commands for buttons, keyboard, and future voice controls", () => {
    expect(rehearsalCommands).toEqual([
      "next",
      "back",
      "repeat-cue",
      "hear-line",
      "pause",
      "resume",
      "stop",
      "bookmark",
      "start-timing"
    ]);
  });
});
