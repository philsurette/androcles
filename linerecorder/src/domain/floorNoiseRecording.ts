import type { RecordingTakeInputQuality } from "./take";
import type { MicrophoneMode } from "../platform/microphone";

export type FloorNoiseRecording = {
  id: string;
  projectId: string;
  recordedAt: string;
  durationMs: number;
  sampleRateHz: number;
  channels: number;
  deviceId: string;
  deviceLabel: string;
  mode: MicrophoneMode;
  inputQuality?: RecordingTakeInputQuality;
  blob: Blob;
};
