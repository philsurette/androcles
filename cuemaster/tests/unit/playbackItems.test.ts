import { describe, expect, it } from "vitest";
import { cuePlaybackItems, responsePlaybackItems, speakAlongPlaybackItems } from "../../src/rehearsal/playbackItems";
import type { Cue } from "../../src/domain/cue";
import type { Line } from "../../src/domain/line";

const cue: Cue = {
  speaker: "_NARRATOR",
  text: "Prologue",
  audioPath: "audio/cue.wav",
  durationMs: 1000
};

const line: Line = {
  id: "line",
  partId: 0,
  blockId: "0.1",
  role: "MEGAERA",
  speaker: "MEGAERA",
  cue,
  responseText: "I won't go another step.",
  responseSegments: [
    {
      id: "segment",
      owners: ["MEGAERA"],
      text: "I won't go another step.",
      audioPath: "audio/response.wav",
      durationMs: 1200,
      simultaneous: false
    }
  ],
  previousRoles: ["_NARRATOR"]
};

describe("playbackItems", () => {
  it("forces cue playback to normal speed", () => {
    expect(cuePlaybackItems([cue])).toEqual([{ path: "audio/cue.wav", playbackRate: 1 }]);
  });

  it("uses selected response speed for actor lines", () => {
    expect(responsePlaybackItems(line, 0.7)).toEqual([{ path: "audio/response.wav", playbackRate: 0.7 }]);
  });

  it("builds speak-along queue as cue then response", () => {
    expect(speakAlongPlaybackItems([cue], line, 0.8)).toEqual([
      { path: "audio/cue.wav", playbackRate: 1 },
      { path: "audio/response.wav", playbackRate: 0.8 }
    ]);
  });
});
