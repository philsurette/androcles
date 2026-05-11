export type RehearsalSession = {
  playbookId: string;
  roleId: string;
  lineIndex: number;
  cueDepth: number;
  includeDirections: boolean;
  revealLine: boolean;
  showLinesByDefault: boolean;
  cueWindowPresetId: string;
  playbackRate: number;
  speakAlongEnabled: boolean;
  speakAlongPauseMs: number;
  tempoTargetHesitationMs: number;
  syncPracticeTiming: boolean;
  tempoTimingPreferred: boolean;
  updatedAt: number;
};
