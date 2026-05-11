import type { Cue } from "../domain/cue";
import type { Line } from "../domain/line";
import type { AudioQueueItem, QueueItem } from "./audioQueue";
import { timingTargetsForLine } from "./tempoFeedback";

export function cuePlaybackItems(cues: Cue[]): AudioQueueItem[] {
  return cues.map((cue) => ({ kind: "audio", path: cue.audioPath, playbackRate: 1 }));
}

export function responsePlaybackItems(line: Line, playbackRate: number): AudioQueueItem[] {
  return line.responseSegments.map((segment) => ({ kind: "audio", path: segment.audioPath, playbackRate }));
}

export function speakAlongPlaybackItems(cues: Cue[], line: Line, playbackRate: number): QueueItem[] {
  return [
    ...cuePlaybackItems(cues),
    { kind: "delay", durationMs: timingTargetsForLine(line).targetHesitationMs },
    ...responsePlaybackItems(line, playbackRate)
  ];
}
