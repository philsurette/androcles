import { describe, expect, it } from "vitest";
import { clampPlaybackRate, visibleCuesForDisplay } from "../../src/ui/screens/RehearsalScreen";

describe("clampPlaybackRate", () => {
  it("clamps response playback speed to the supported range", () => {
    expect(clampPlaybackRate(0.1)).toBe(0.4);
    expect(clampPlaybackRate(1.8)).toBe(1.3);
  });

  it("rounds response playback speed to one decimal place", () => {
    expect(clampPlaybackRate(0.94)).toBe(0.9);
    expect(clampPlaybackRate(0.95)).toBe(1);
  });
});

describe("visibleCuesForDisplay", () => {
  it("keeps speech cues when directions are off", () => {
    expect(
      visibleCuesForDisplay(
        [
          {
            speaker: "_NARRATOR",
            text: "They cross.",
            audioPath: "audio/direction.wav",
            durationMs: 1000,
            kind: "direction"
          },
          {
            speaker: "CHRISTINE",
            text: "Do you mind if I record?",
            audioPath: "audio/speech.wav",
            durationMs: 1000,
            kind: "speech"
          }
        ],
        false
      ).map((cue) => cue.text)
    ).toEqual(["They cross.", "Do you mind if I record?"]);
  });

  it("replaces hidden direction cues with the preceding speech line", () => {
    expect(
      visibleCuesForDisplay(
        [
          {
            speaker: "_NARRATOR",
            text: "They cross.",
            audioPath: "audio/direction.wav",
            durationMs: 1000
          }
        ],
        false,
        [
          {
            id: "I-1",
            partId: 0,
            blockId: "0.1",
            kind: "direction",
            speaker: "_NARRATOR",
            text: "They cross.",
            contentHash: "sha256:test",
            audioPath: "audio/direction.wav",
            durationMs: 1000
          }
        ],
        {
          id: "fairies",
          title: "Fairies",
          authors: [],
          schemaVersion: 1,
          sections: [],
          context: [],
          roles: [
            {
              id: "CHRISTINE",
              displayName: "Christine",
              reader: "Reader",
              parts: [],
              lines: [
                {
                  id: "2-3",
                  partId: 2,
                  blockId: "2.3",
                  role: "CHRISTINE",
                  speaker: "CHRISTINE",
                  contentHash: "sha256:test",
                  cue: {
                    speaker: "LILLIAN",
                    text: "My aunt Emma...",
                    audioPath: "audio/lillian.wav",
                    durationMs: 1000
                  },
                  responseText: "Theosophy? Could you define that for the readers?",
                  responseSegments: [
                    {
                      id: "2-3:s1",
                      segmentId: "2_3_1",
                      contentHash: "sha256:test",
                      owners: ["CHRISTINE"],
                      text: "Theosophy? Could you define that for the readers?",
                      audioPath: "audio/christine.wav",
                      durationMs: 2200,
                      simultaneous: false
                    }
                  ],
                  directions: [],
                  previousRoles: []
                }
              ]
            }
          ]
        },
        {
          id: "2-5",
          partId: 2,
          blockId: "2.5",
          role: "LILLIAN",
          speaker: "LILLIAN",
          contentHash: "sha256:test",
          cue: {
            speaker: "_NARRATOR",
            text: "They cross.",
            audioPath: "audio/direction.wav",
            durationMs: 1000
          },
          responseText: "It was a sort of new religion.",
          responseSegments: [],
          directions: [],
          previousRoles: []
        }
      )
    ).toEqual([
      {
        speaker: "CHRISTINE",
        text: "Theosophy? Could you define that for the readers?",
        audioPath: "audio/christine.wav",
        durationMs: 2200,
        kind: "speech"
      }
    ]);
  });
});
