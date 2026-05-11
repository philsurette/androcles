export type TakeStatus = "recorded" | "accepted" | "replaced";

export type RecordingTake = {
  id: string;
  projectId: string;
  segmentId: string;
  status: TakeStatus;
  recordedAt: string;
  durationMs: number;
  sampleRateHz: number;
  channels: number;
  blob: Blob;
};
