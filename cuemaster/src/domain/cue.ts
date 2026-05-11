export type Cue = {
  speaker: string;
  text: string;
  audioPath: string;
  durationMs: number;
  cueStartOffsets?: CueStartOffset[];
};

export type CueStartOffset = {
  requestedWindowMs: number;
  startMs: number;
  confidence: "exact" | "boundary" | "fallback";
};
