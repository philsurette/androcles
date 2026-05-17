import { describe, expect, it, vi } from "vitest";
import manifestFixture from "../fixtures/minimal-playbook/manifest.json";
import type { PlaybookManifest } from "../../src/specs/playbookManifest";
import { validatePlaybookManifest } from "../../src/specs/validatePlaybookManifest";

describe("validatePlaybookManifest", () => {
  it("accepts a Stager-shaped manifest with narrator context and actor roles", () => {
    const manifest = validatePlaybookManifest(manifestFixture);

    expect(manifest.format_version).toBe("1.0.0");
    expect(manifest.package_type).toBe("playbook");
    expect(manifest.context[0].speaker).toBe("_NARRATOR");
    expect(manifest.roles.map((role) => role.id)).toEqual(["ANDROCLES", "MEGAERA"]);
  });

  it("accepts a newer patch format without warning", () => {
    const manifest = structuredClone(manifestFixture);
    manifest.format_version = "1.0.1";
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);

    expect(validatePlaybookManifest(manifest).format_version).toBe("1.0.1");
    expect(warn).not.toHaveBeenCalled();

    warn.mockRestore();
  });

  it("accepts a newer minor format with a warning", () => {
    const manifest = structuredClone(manifestFixture);
    manifest.format_version = "1.1.0";
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);

    expect(validatePlaybookManifest(manifest).format_version).toBe("1.1.0");
    expect(warn).toHaveBeenCalledWith(
      "playbook format version 1.1.0 is newer than supported 1.0.0; newer features may be ignored."
    );

    warn.mockRestore();
  });

  it("rejects a newer major format", () => {
    const manifest = structuredClone(manifestFixture);
    manifest.format_version = "2.0.0";

    expect(() => validatePlaybookManifest(manifest)).toThrow(
      "Unsupported playbook format version 2.0.0; supported version is 1.0.0"
    );
  });

  it("rejects a missing format version", () => {
    const manifest = structuredClone(manifestFixture) as Partial<PlaybookManifest>;
    delete manifest.format_version;

    expect(() => validatePlaybookManifest(manifest)).toThrow("playbook package is missing format_version");
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

  it("rejects parser-shaped ids for production script units", () => {
    const invalid = structuredClone(manifestFixture);
    invalid.context[0].id = "0_0_1";

    expect(() => validatePlaybookManifest(invalid)).toThrow("Expected a production id");
  });

  it("rejects a malformed cue audio reference", () => {
    const invalid = structuredClone(manifestFixture);
    invalid.roles[0].lines[0].cue.audio.path = "";

    expect(() => validatePlaybookManifest(invalid)).toThrow();
  });

  it("accepts no-cue zero-window offsets emitted by Stager", () => {
    const manifest = structuredClone(manifestFixture) as PlaybookManifest;
    manifest.roles[0].lines[0].cue.audio.cue_start_offsets = [
      {
        requested_window_ms: 0,
        start_ms: 0,
        confidence: "exact"
      }
    ];

    expect(validatePlaybookManifest(manifest).roles[0].lines[0].cue.audio.cue_start_offsets?.[0]).toMatchObject({
      requested_window_ms: 0
    });
  });

  it("accepts blocking context without audio and line blocking ids", () => {
    const manifest = structuredClone(manifestFixture) as PlaybookManifest;
    manifest.context.push({
      id: "I-2",
      part_id: 0,
      block_id: "0.2",
      kind: "blocking",
      speaker: "_NARRATOR",
      targets: ["MEGAERA"],
      placement: "before",
      text: "Crosses downstage.",
      content_hash: "sha256:0000000000000000000000000000000000000000000000000000000000000021"
    });
    manifest.roles[0].lines[0].blocking = [
      {
        id: "I-1:b1",
        segment_id: "0_1_2",
        content_hash: "sha256:0000000000000000000000000000000000000000000000000000000000000022",
        targets: ["ANDROCLES"],
        text: "takes MEGAERA's hand",
        placement: "inline"
      }
    ];

    expect(validatePlaybookManifest(manifest).context.at(-1)?.kind).toBe("blocking");
    expect(validatePlaybookManifest(manifest).roles[0].lines[0].blocking?.[0].id).toBe("I-1:b1");
  });
});
