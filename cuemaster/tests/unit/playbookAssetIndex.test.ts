import { describe, expect, it } from "vitest";
import { PlaybookAssetIndex, collectRequiredAudioAssetPaths } from "../../src/playbook/playbookAssetIndex";
import { validatePlaybookManifest } from "../../src/specs/validatePlaybookManifest";
import manifestFixture from "../fixtures/minimal-playbook/manifest.json";

describe("PlaybookAssetIndex", () => {
  it("normalizes leading slashes when checking asset paths", () => {
    const index = new PlaybookAssetIndex(["audio/segments/ANDROCLES/0_1_1.wav"]);

    expect(index.has("/audio/segments/ANDROCLES/0_1_1.wav")).toBe(true);
  });

  it("collects required cue, response, context, and top-level audio assets once", () => {
    const requiredPaths = collectRequiredAudioAssetPaths(validatePlaybookManifest(manifestFixture));

    expect(requiredPaths).toEqual([
      "audio/segments/ANDROCLES/0_1_1.wav",
      "audio/segments/ANDROCLES/0_3_1.wav",
      "audio/segments/MEGAERA/0_2_1.wav",
      "audio/segments/_NARRATOR/0_0_1.wav"
    ]);
  });
});
