import type { Cue } from "./cue";

export type ResponseSegment = {
  id: string;
  owners: string[];
  text: string;
  audioPath: string;
  durationMs: number;
  simultaneous: boolean;
};

export type LineTiming = {
  targetHesitationMs?: number;
};

export type Line = {
  id: string;
  partId: number | null;
  blockId: string;
  role: string;
  speaker: string;
  cue: Cue;
  responseText: string;
  responseSegments: ResponseSegment[];
  previousRoles: string[];
  timing?: LineTiming;
};
