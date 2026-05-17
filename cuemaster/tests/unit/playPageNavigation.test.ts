import { describe, expect, it } from "vitest";
import type { Section } from "../../src/domain/section";
import type { PlayPageEntry } from "../../src/rehearsal/playPageEntries";
import {
  nextLineIndex,
  nextRoleLineIndex,
  nextSectionStartIndex,
  previousLineIndex,
  previousRoleLineIndex,
  previousSectionStartIndex,
  sectionIndexByPartId,
  sectionWindowForIndex
} from "../../src/rehearsal/playPageNavigation";

describe("play page navigation", () => {
  const entries = [
    contextEntry("intro", null, "_NARRATOR"),
    contextEntry("a-1", 1, "Lavinia"),
    contextEntry("a-2", 1, "_LAVINIA"),
    contextEntry("b-1", 2, "Androcles"),
    contextEntry("b-2", 2, "Lavinia")
  ];
  const sections: Section[] = [
    { id: "intro", partId: null, blockId: null, title: "Intro", ordinal: 0 },
    { id: "act-1", partId: 1, blockId: "1", title: "Act I", ordinal: 1 },
    { id: "act-2", partId: 2, blockId: "2", title: "Act II", ordinal: 2 }
  ];
  const sectionMap = sectionIndexByPartId(sections);

  it("finds neighboring entries", () => {
    expect(previousLineIndex(entries, 0)).toBe(-1);
    expect(previousLineIndex(entries, 2)).toBe(1);
    expect(nextLineIndex(entries, 2)).toBe(3);
    expect(nextLineIndex(entries, entries.length - 1)).toBe(-1);
  });

  it("finds neighboring entries for the current role", () => {
    expect(previousRoleLineIndex(entries, 4, "LAVINIA")).toBe(2);
    expect(nextRoleLineIndex(entries, 1, "lavinia")).toBe(2);
    expect(nextRoleLineIndex(entries, 2, "LAVINIA")).toBe(4);
    expect(previousRoleLineIndex(entries, 3, "ANDROCLES")).toBe(-1);
  });

  it("finds section boundaries", () => {
    expect(previousSectionStartIndex(entries, 2, sectionMap, sections)).toBe(1);
    expect(previousSectionStartIndex(entries, 1, sectionMap, sections)).toBe(0);
    expect(previousSectionStartIndex(entries, 0, sectionMap, sections)).toBe(-1);
    expect(nextSectionStartIndex(entries, 1, sectionMap, sections)).toBe(3);
    expect(nextSectionStartIndex(entries, 3, sectionMap, sections)).toBe(-1);
  });

  it("returns the current section window", () => {
    expect(sectionWindowForIndex(entries, 2, sectionMap, sections)).toEqual({
      start: 1,
      end: 3,
      label: "Act I"
    });
    expect(sectionWindowForIndex(entries, -1, sectionMap, sections)).toEqual({
      start: 0,
      end: entries.length,
      label: "Intro"
    });
  });
});

function contextEntry(id: string, partId: number | null, speaker: string): PlayPageEntry {
  return {
    type: "context",
    id,
    blockId: id,
    partId,
    speaker,
    text: id,
    audioPath: `audio/${id}.wav`,
    sourceOrder: 0
  };
}
