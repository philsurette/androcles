export type RecordingItem = {
  lineId: string;
  blockId: string;
  segmentId: string;
  sequence: number;
  displayText: string;
  segmentText: string;
  outputPath: string;
  cueText?: string;
  sectionId?: string;
  sectionTitle?: string;
  sceneHeading?: string;
  stageDirections: string[];
  notes?: string;
  changed?: boolean;
  targetDurationMs?: number;
  targetHesitationMs?: number;
  simultaneous?: boolean;
};
