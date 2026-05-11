import { describe, expect, it } from "vitest";
import {
  cuePlaybackItems,
  cueStartTimeMs,
  responsePlaybackItems,
  speakAlongPlaybackItems
} from "../../src/rehearsal/playbackItems";
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
  directions: [],
  previousRoles: ["_NARRATOR"]
};

describe("playbackItems", () => {
  it("forces cue playback to normal speed", () => {
    expect(cuePlaybackItems([cue])).toEqual([{ kind: "audio", path: "audio/cue.wav", playbackRate: 1 }]);
  });

  it("starts a single long cue at the selected absolute cue window", () => {
    const longCue: Cue = { ...cue, audioPath: "audio/long-cue.wav", durationMs: 30000 };

    expect(cuePlaybackItems([longCue], "last_10s")).toEqual([
      { kind: "audio", path: "audio/long-cue.wav", playbackRate: 1, startTimeMs: 20000 }
    ]);
  });

  it("snaps the first cue trim up to the next shared cue window when a timed window spans multiple cues", () => {
    const earlierCue: Cue = { ...cue, audioPath: "audio/earlier-cue.wav", durationMs: 20000 };
    const finalCue: Cue = { ...cue, audioPath: "audio/final-cue.wav", durationMs: 6000 };

    expect(cuePlaybackItems([earlierCue, finalCue], "last_10s")).toEqual([
      { kind: "audio", path: "audio/earlier-cue.wav", playbackRate: 1, startTimeMs: 15000 },
      { kind: "audio", path: "audio/final-cue.wav", playbackRate: 1 }
    ]);
  });

  it("uses Stager offsets for the snapped cue window", () => {
    const earlierCue: Cue = {
      ...cue,
      audioPath: "audio/earlier-cue.wav",
      durationMs: 24000,
      cueStartOffsets: [{ requestedWindowMs: 10000, startMs: 13250, confidence: "boundary" }]
    };
    const finalCue: Cue = { ...cue, audioPath: "audio/final-cue.wav", durationMs: 14000 };

    expect(cuePlaybackItems([earlierCue, finalCue], "last_20s")).toEqual([
      { kind: "audio", path: "audio/earlier-cue.wav", playbackRate: 1, startTimeMs: 13250 },
      { kind: "audio", path: "audio/final-cue.wav", playbackRate: 1 }
    ]);
  });

  it("plays the full cue when the selected cue window is longer than the cue", () => {
    expect(cuePlaybackItems([cue], "last_5s")).toEqual([{ kind: "audio", path: "audio/cue.wav", playbackRate: 1 }]);
  });

  it("prefers Stager-provided cue start offsets when they are present", () => {
    expect(
      cueStartTimeMs(
        {
          ...cue,
          durationMs: 30000,
          cueStartOffsets: [{ requestedWindowMs: 10000, startMs: 18500, confidence: "boundary" }]
        },
        "last_10s"
      )
    ).toBe(18500);
  });

  it("uses selected response speed for actor lines", () => {
    expect(responsePlaybackItems(line, 0.7)).toEqual([{ kind: "audio", path: "audio/response.wav", playbackRate: 0.7 }]);
  });

  it("builds speak-along queue as cue, pickup delay, then response", () => {
    expect(speakAlongPlaybackItems([cue], line, 0.8)).toEqual([
      { kind: "audio", path: "audio/cue.wav", playbackRate: 1 },
      { kind: "delay", durationMs: 750 },
      { kind: "audio", path: "audio/response.wav", playbackRate: 0.8 }
    ]);
  });

  it("uses line-specific target hesitation for the speak-along delay", () => {
    const longCue = { ...cue, durationMs: 30000 };
    expect(speakAlongPlaybackItems([longCue], { ...line, timing: { targetHesitationMs: 1200 } }, 0.8, "last_10s")).toEqual([
      { kind: "audio", path: "audio/cue.wav", playbackRate: 1, startTimeMs: 20000 },
      { kind: "delay", durationMs: 1200 },
      { kind: "audio", path: "audio/response.wav", playbackRate: 0.8 }
    ]);
  });

  it("uses explicit speak-along pause when supplied", () => {
    expect(speakAlongPlaybackItems([cue], line, 0.8, "full", 1000)).toEqual([
      { kind: "audio", path: "audio/cue.wav", playbackRate: 1 },
      { kind: "delay", durationMs: 1000 },
      { kind: "audio", path: "audio/response.wav", playbackRate: 0.8 }
    ]);
  });
});
