import type { ContextKind } from "./context";

export type Cue = {
  speaker: string;
  text: string;
  audioPath: string;
  durationMs: number;
  kind?: ContextKind | "speech";
  cueStartOffsets?: CueStartOffset[];
};

export type CueStartOffset = {
  requestedWindowMs: number;
  startMs: number;
  confidence: "exact" | "boundary" | "fallback";
};
