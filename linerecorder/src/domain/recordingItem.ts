export type RecordingItemBlocking = {
  id: string;
  targets: string[];
  text: string;
  placement: "inline" | "standalone";
};

export type RecordingItem = {
  id: string;
  lineId: string;
  blockId: string;
  segmentId: string;
  lineContentHash: string;
  segmentContentHash: string;
  sequence: number;
  displayText: string;
  segmentText: string;
  outputPath: string;
  cueText?: string;
  cueSpeaker?: string;
  previousText?: string;
  previousSpeaker?: string;
  nextText?: string;
  nextSpeaker?: string;
  sectionId?: string;
  sectionTitle?: string;
  sceneHeading?: string;
  stageDirections: string[];
  blocking: RecordingItemBlocking[];
  reason?: string;
  notes?: string;
  changed?: boolean;
  cueAudio?: string;
  previousRecording?: string;
  targetDurationMs?: number;
  targetHesitationMs?: number;
  simultaneous?: boolean;
};
