export type TakeStatus = "recorded" | "accepted" | "replaced";

export type RecordingTakeInputQuality = {
  peakEnergy: number;
  levelCounts: {
    noSignal: number;
    tooQuiet: number;
    good: number;
    clipping: number;
  };
};

export type RecordingTake = {
  id: string;
  projectId: string;
  segmentId: string;
  status: TakeStatus;
  recordedAt: string;
  durationMs: number;
  sampleRateHz: number;
  channels: number;
  inputQuality?: RecordingTakeInputQuality;
  blob: Blob;
};
