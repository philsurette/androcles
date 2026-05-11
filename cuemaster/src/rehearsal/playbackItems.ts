import type { Cue } from "../domain/cue";
import type { Line } from "../domain/line";
import type { AudioQueueItem } from "./audioQueue";

export function cuePlaybackItems(cues: Cue[]): AudioQueueItem[] {
  return cues.map((cue) => ({ path: cue.audioPath, playbackRate: 1 }));
}

export function responsePlaybackItems(line: Line, playbackRate: number): AudioQueueItem[] {
  return line.responseSegments.map((segment) => ({ path: segment.audioPath, playbackRate }));
}

export function speakAlongPlaybackItems(cues: Cue[], line: Line, playbackRate: number): AudioQueueItem[] {
  return [...cuePlaybackItems(cues), ...responsePlaybackItems(line, playbackRate)];
}
