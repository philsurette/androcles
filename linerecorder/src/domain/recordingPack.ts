import type { RecordingItem } from "./recordingItem";

export type RecordingPackPlay = {
  id: string;
  title: string;
  version?: string;
};

export type RecordingPackRole = {
  id: string;
  displayName: string;
};

export type RecordingPreferences = {
  preferredSampleRateHz: number;
  preferredChannels: number;
  sourceFormat: "wav";
};

export type RecordingPack = {
  schemaVersion: 1;
  packageType: "role_recording_pack";
  play: RecordingPackPlay;
  role: RecordingPackRole;
  recording: RecordingPreferences;
  items: RecordingItem[];
};
