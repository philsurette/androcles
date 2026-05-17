import { describe, expect, it } from "vitest";
import type { Playbook } from "../../src/domain/playbook";
import {
  buildDirectionAudioPathLookup,
  buildPlayEntries,
  compareSegmentIds
} from "../../src/rehearsal/playPageEntries";

describe("play page entries", () => {
  it("builds ordered context and line entries with inline direction audio", () => {
    const playbook = playbookFixture();
    const lookup = buildDirectionAudioPathLookup(playbook);
    const entries = buildPlayEntries(playbook, true, lookup);

    expect(entries.map((entry) => `${entry.type}:${entry.id}`)).toEqual([
      "context:I-1:d1",
      "line:I-1",
      "line:I-2"
    ]);
    expect(entries[1]).toMatchObject({
      type: "line",
      id: "I-1",
      inlineDirectionAudioPaths: [
        {
          segmentId: "I_1_d1",
          path: "audio/segments/NARRATOR/I_1_d1.wav"
        }
      ]
    });
  });

  it("omits narration context and inline direction audio when narration is off", () => {
    const entries = buildPlayEntries(playbookFixture(), false, buildDirectionAudioPathLookup(playbookFixture()));

    expect(entries.map((entry) => entry.type)).toEqual(["line", "line"]);
    expect(entries[0]).toMatchObject({ inlineDirectionAudioPaths: [] });
  });

  it("compares segment ids using numeric portions", () => {
    expect(compareSegmentIds("I_1_2", "I_1_10")).toBeLessThan(0);
    expect(compareSegmentIds("I_1_d1", "I_1_d1")).toBe(0);
  });
});

function playbookFixture(): Playbook {
  return {
    id: "androcles",
    title: "Androcles",
    authors: [],
    production: { source: "working" },
    schemaVersion: 1,
    sections: [],
    context: [
      {
        id: "I-1:d1",
        partId: 1,
        blockId: "1.1",
        kind: "direction",
        speaker: "_NARRATOR",
        text: "They enter.",
        contentHash: "sha256:direction",
        audioPath: "audio/context/I_1_d1.wav",
        durationMs: 1000
      }
    ],
    audioAssetPaths: [
      "audio/segments/NARRATOR/I_1_d1.wav"
    ],
    roles: [
      {
        id: "LAVINIA",
        displayName: "Lavinia",
        reader: "Reader",
        parts: [],
        lines: [
          {
            id: "I-2",
            partId: 1,
            blockId: "1.2",
            role: "LAVINIA",
            speaker: "LAVINIA",
            contentHash: "sha256:line2",
            cue: {
              speaker: "ANDROCLES",
              text: "Second cue.",
              audioPath: "audio/segments/ANDROCLES/I_2_cue.wav",
              durationMs: 500
            },
            responseText: "Second line.",
            responseSegments: [],
            directions: [],
            previousRoles: []
          },
          {
            id: "I-1",
            partId: 1,
            blockId: "1.1",
            role: "LAVINIA",
            speaker: "LAVINIA",
            contentHash: "sha256:line1",
            cue: {
              speaker: "_NARRATOR",
              text: "They enter.",
              audioPath: "audio/segments/NARRATOR/I_1_cue.wav",
              durationMs: 500
            },
            responseText: "First line.",
            responseSegments: [
              {
                id: "I-1:s1",
                segmentId: "I_1_1",
                contentHash: "sha256:segment",
                owners: ["LAVINIA"],
                text: "First line.",
                audioPath: "audio/segments/LAVINIA/I_1_1.wav",
                durationMs: 1000,
                simultaneous: false
              }
            ],
            directions: [
              {
                id: "I-1:d1",
                segmentId: "I_1_d1",
                contentHash: "sha256:inline",
                text: "aside",
                placement: "inline"
              }
            ],
            previousRoles: []
          }
        ]
      }
    ]
  };
}
