import type { RecordingItem } from "./recordingItem";

export type RecordingRequestPlay = {
  id: string;
  title: string;
  version?: string;
};

export type RecordingRequestRole = {
  id: string;
  displayName: string;
};

export type RecordingPreferences = {
  preferredSampleRateHz: number;
  preferredChannels: number;
  sourceFormat: "wav";
};

export type RecordingRequestMetadata = {
  id: string;
  kind: "full_role" | "selected_segments" | "rerecord";
  createdAt: string;
  createdBy: string;
  productionVersion?: string;
  notes?: string;
};

export type ProductionMetadata = {
  source: "published" | "working";
  version?: string;
  sequence?: number;
  publicationId?: string;
  parentVersion?: string;
  publishedAt?: string;
};

export type RecordingRequest = {
  schemaVersion: 1;
  packageType: "recording_request";
  request: RecordingRequestMetadata;
  play: RecordingRequestPlay;
  production: ProductionMetadata;
  role: RecordingRequestRole;
  recording: RecordingPreferences;
  items: RecordingItem[];
};
