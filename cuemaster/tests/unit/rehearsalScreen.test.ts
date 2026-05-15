import { describe, expect, it } from "vitest";
import {
  clampPlaybackRate,
  outlineSearchText,
  resolveCurrentLineFromEngine,
  visibleCuesForDisplay
} from "../../src/ui/screens/RehearsalScreen";
import type { Line } from "../../src/domain/line";
import type { Playbook } from "../../src/domain/playbook";

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

describe("outlineSearchText", () => {
  const playbook: Playbook = {
    id: "fairies",
    title: "Fairies",
    authors: [],
    schemaVersion: 1,
    sections: [],
    context: [],
    roles: []
  };

  const line: Line = {
    id: "2-3:s1",
    partId: 2,
    blockId: "2.3",
    role: "LILLIAN",
    speaker: "LILLIAN",
    contentHash: "sha256:test",
    cue: {
      speaker: "CHRISTINE",
      text: "Do you mind if I record?",
      audioPath: "audio/christine.wav",
      durationMs: 1000,
      kind: "speech"
    },
    responseText: "Please do.",
    responseSegments: [],
    directions: [
      {
        id: "2-3:d1",
        segmentId: "2_3_d1",
        contentHash: "sha256:direction",
        text: "softly",
        placement: "inline"
      }
    ],
    previousRoles: [],
    blocking: [
      {
        id: "2-3:b1",
        contentHash: "sha256:blocking",
        placement: "before",
        targets: ["LILLIAN"],
        text: "settles beside the recorder"
      }
    ]
  };

  it("matches cue text and response text in cue mode", () => {
    const text = outlineSearchText(line, "cues", true, true, "role", playbook).toLocaleLowerCase();

    expect(text).toContain("do you mind");
    expect(text).toContain("2-3:s1");
  });

  it("does not include cue text in line mode", () => {
    const text = outlineSearchText(line, "lines", true, true, "role", playbook).toLocaleLowerCase();

    expect(text).not.toContain("do you mind");
    expect(text).toContain("please do");
  });

  it("matches visible blocking text", () => {
    expect(outlineSearchText(line, "lines", true, true, "role", playbook)).toContain("settles beside the recorder");
    expect(outlineSearchText(line, "lines", true, false, "role", playbook)).not.toContain(
      "settles beside the recorder"
    );
  });
});

describe("resolveCurrentLineFromEngine", () => {
  const lines: Line[] = [
    {
      id: "line-1",
      partId: 1,
      blockId: "1.1",
      role: "CHRISTINE",
      speaker: "CHRISTINE",
      contentHash: "sha256:line1",
      cue: {
        speaker: "NARRATOR",
        text: "Line one cue",
        audioPath: "audio/line-1.wav",
        durationMs: 500
      },
      responseText: "Line one response",
      responseSegments: [],
      directions: [],
      previousRoles: []
    },
    {
      id: "line-2",
      partId: 1,
      blockId: "1.2",
      role: "CHRISTINE",
      speaker: "CHRISTINE",
      contentHash: "sha256:line2",
      cue: {
        speaker: "NARRATOR",
        text: "Line two cue",
        audioPath: "audio/line-2.wav",
        durationMs: 600
      },
      responseText: "Line two response",
      responseSegments: [],
      directions: [],
      previousRoles: []
    }
  ];

  const fallbackLine: Line = {
    id: "line-stale",
    partId: 1,
    blockId: "1.f",
    role: "CHRISTINE",
    speaker: "CHRISTINE",
    contentHash: "sha256:stale",
    cue: {
      speaker: "NARRATOR",
      text: "Stale cue",
      audioPath: "audio/stale.wav",
      durationMs: 100
    },
    responseText: "Stale response",
    responseSegments: [],
    directions: [],
    previousRoles: []
  };

  it("uses the engine-position line when available", () => {
    const lineFromEngine = resolveCurrentLineFromEngine(lines, 1, fallbackLine);

    expect(lineFromEngine?.id).toBe("line-2");
  });

  it("falls back only when engine-position line is unavailable", () => {
    const lineFromEngine = resolveCurrentLineFromEngine(lines, 10, fallbackLine);

    expect(lineFromEngine?.id).toBe("line-stale");
  });
});
