import { describe, expect, it } from "vitest";
import { fairiesDemoManifest } from "../../src/fixtures/fairiesDemoManifest";
import { PlaybookNormalizer } from "../../src/playbook/normalizePlaybook";
import { RoleRehearsalSequenceBuilder, WholePlaySequenceBuilder } from "../../src/playback/playbackSequence";

const playbook = new PlaybookNormalizer().normalize(fairiesDemoManifest);
const lillian = playbook.roles.find((role) => role.id === "LILLIAN");

describe("RoleRehearsalSequenceBuilder", () => {
  it("builds role-only rehearsal steps from playbook cue and response assets", () => {
    const line = lillian?.lines[0];
    if (line === undefined) {
      throw new Error("Missing LILLIAN fixture line.");
    }

    expect(new RoleRehearsalSequenceBuilder().build(line, "try_then_check", 1).map((step) => step.kind)).toEqual([
      "audio",
      "wait",
      "audio",
      "advance"
    ]);
  });
});

describe("WholePlaySequenceBuilder", () => {
  it("includes context entries and role responses in play order", () => {
    const items = new WholePlaySequenceBuilder().build(playbook);

    expect(items.map((item) => item.id)).toContain("P-1");
    expect(items.map((item) => item.id)).toContain("P-3");
    expect(items.find((item) => item.id === "P-3")?.blocking.map((blocking) => blocking.text)).toEqual([
      "@ interview_chair face=CHRISTINE"
    ]);
  });
});
