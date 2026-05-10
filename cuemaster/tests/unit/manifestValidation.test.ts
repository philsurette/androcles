import { describe, expect, it } from "vitest";
import manifestFixture from "../fixtures/minimal-playbook/manifest.json";
import { validatePlaybookManifest } from "../../src/specs/validatePlaybookManifest";

describe("validatePlaybookManifest", () => {
  it("accepts a Stager-shaped manifest with narrator context and actor roles", () => {
    const manifest = validatePlaybookManifest(manifestFixture);

    expect(manifest.context[0].speaker).toBe("_NARRATOR");
    expect(manifest.roles.map((role) => role.id)).toEqual(["ANDROCLES", "MEGAERA"]);
  });

  it("rejects a role without a line array", () => {
    const invalid = structuredClone(manifestFixture);
    delete (invalid.roles[0] as Partial<(typeof invalid.roles)[number]>).lines;

    expect(() => validatePlaybookManifest(invalid)).toThrow();
  });

  it("rejects a line without an id", () => {
    const invalid = structuredClone(manifestFixture);
    delete (invalid.roles[0].lines[0] as Partial<(typeof invalid.roles)[number]["lines"][number]>).id;

    expect(() => validatePlaybookManifest(invalid)).toThrow();
  });

  it("rejects a malformed cue audio reference", () => {
    const invalid = structuredClone(manifestFixture);
    invalid.roles[0].lines[0].cue.audio.path = "";

    expect(() => validatePlaybookManifest(invalid)).toThrow();
  });
});
