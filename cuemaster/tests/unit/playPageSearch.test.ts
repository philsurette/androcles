import { describe, expect, it } from "vitest";
import {
  entryMatchesSearchQuery,
  entrySearchHaystack,
  entryTokensForSearch,
  isLikelyIdQuery,
  type SearchablePlayPageEntry
} from "../../src/rehearsal/playPageSearch";

describe("play page search", () => {
  const entry: SearchablePlayPageEntry = {
    type: "line",
    id: "I-3",
    speaker: "LAVINIA",
    text: "The words of the Christians are strange.",
    line: {
      directions: [
        {
          id: "I-3:d1",
          segmentId: "I_3_d1",
          contentHash: "sha256:direction",
          text: "crossing to the gate",
          placement: "inline"
        }
      ]
    }
  };

  it("matches ordinary text against title, speaker, text, and directions", () => {
    expect(entrySearchHaystack(entry, "Androcles")).toContain("crossing to the gate");
    expect(entryMatchesSearchQuery(entry, "christians", "Androcles")).toBe(true);
    expect(entryMatchesSearchQuery(entry, "gate", "Androcles")).toBe(true);
  });

  it("uses exact token matching for likely line id queries", () => {
    expect(isLikelyIdQuery("i-3")).toBe(true);
    expect(entryMatchesSearchQuery(entry, "i-3", "Androcles")).toBe(true);
    expect(entryMatchesSearchQuery(entry, "i-4", "Androcles")).toBe(false);
  });

  it("tokenizes searchable fields for id lookup", () => {
    expect(entryTokensForSearch(entry, "Androcles")).toContain("i-3");
    expect(entryTokensForSearch(entry, "Androcles")).toContain("lavinia");
  });
});
