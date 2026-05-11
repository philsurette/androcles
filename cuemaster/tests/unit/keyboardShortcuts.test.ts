import { describe, expect, it } from "vitest";
import { shortcutForKey } from "../../src/rehearsal/keyboardShortcuts";

describe("shortcutForKey", () => {
  it("maps desk rehearsal keys to actions", () => {
    expect(shortcutForKey({ key: " ", target: null })).toBe("toggle-playback");
    expect(shortcutForKey({ key: "R", target: null })).toBe("repeat-cue");
    expect(shortcutForKey({ key: "ArrowRight", target: null })).toBe("next");
    expect(shortcutForKey({ key: "ArrowLeft", target: null })).toBe("previous");
    expect(shortcutForKey({ key: "L", target: null })).toBe("hear-line");
    expect(shortcutForKey({ key: "Escape", target: null })).toBe("stop");
  });

  it("ignores shortcuts from editable controls", () => {
    expect(shortcutForKey({ key: "R", target: document.createElement("input") })).toBeNull();
    expect(shortcutForKey({ key: "ArrowRight", target: document.createElement("select") })).toBeNull();
  });

  it("ignores unmapped keys", () => {
    expect(shortcutForKey({ key: "Tab", target: null })).toBeNull();
  });
});
