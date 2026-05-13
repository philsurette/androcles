import type { Cue } from "./cue";

export type ResponseSegment = {
  id: string;
  segmentId: string;
  contentHash: string;
  owners: string[];
  text: string;
  audioPath: string;
  durationMs: number;
  simultaneous: boolean;
};

export type LineTiming = {
  targetHesitationMs?: number;
};

export type StageDirection = {
  id: string;
  segmentId: string;
  contentHash: string;
  text: string;
  placement: "top_level" | "inline" | "description";
};

export type BlockingNote = {
  id: string;
  segmentId?: string;
  contentHash: string;
  text: string;
  placement: "inline" | "before" | "after";
  targets: string[];
};

export type Line = {
  id: string;
  partId: number | null;
  blockId: string;
  role: string;
  speaker: string;
  contentHash: string;
  cue: Cue;
  responseText: string;
  responseSegments: ResponseSegment[];
  directions: StageDirection[];
  blocking?: BlockingNote[];
  previousRoles: string[];
  timing?: LineTiming;
};
