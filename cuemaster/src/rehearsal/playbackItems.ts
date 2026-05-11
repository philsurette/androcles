import type { Cue } from "../domain/cue";
import type { Line } from "../domain/line";
import type { AudioQueueItem, QueueItem } from "./audioQueue";
import { cueWindowPresetForId } from "./cueWindowPreset";
import { timingTargetsForLine } from "./tempoFeedback";

export function cuePlaybackItems(cues: Cue[], cueWindowPresetId = "full"): AudioQueueItem[] {
  return cues.map((cue, index) => {
    const startTimeMs = index === cues.length - 1 ? cueStartTimeMs(cue, cueWindowPresetId) : undefined;
    return {
      kind: "audio",
      path: cue.audioPath,
      playbackRate: 1,
      ...(startTimeMs === undefined ? {} : { startTimeMs })
    };
  });
}

export function responsePlaybackItems(line: Line, playbackRate: number): AudioQueueItem[] {
  return line.responseSegments.map((segment) => ({ kind: "audio", path: segment.audioPath, playbackRate }));
}

export function speakAlongPlaybackItems(
  cues: Cue[],
  line: Line,
  playbackRate: number,
  cueWindowPresetId = "full"
): QueueItem[] {
  return [
    ...cuePlaybackItems(cues, cueWindowPresetId),
    { kind: "delay", durationMs: timingTargetsForLine(line).targetHesitationMs },
    ...responsePlaybackItems(line, playbackRate)
  ];
}

export function cueStartTimeMs(cue: Cue, cueWindowPresetId: string): number | undefined {
  const preset = cueWindowPresetForId(cueWindowPresetId);
  if (preset.windowMs === null || cue.durationMs <= preset.windowMs) {
    return undefined;
  }

  const offset = cue.cueStartOffsets?.find((candidate) => candidate.requestedWindowMs === preset.windowMs);
  return offset?.startMs ?? cue.durationMs - preset.windowMs;
}
