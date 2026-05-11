export type RehearsalSession = {
  playbookId: string;
  roleId: string;
  lineIndex: number;
  cueDepth: number;
  includeDirections: boolean;
  revealLine: boolean;
  cueWindowPresetId: string;
  playbackRate: number;
  speakAlongEnabled: boolean;
  tempoTimingPreferred: boolean;
  updatedAt: number;
};
