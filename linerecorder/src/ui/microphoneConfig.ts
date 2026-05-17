import type { MicrophoneMode } from "../platform/microphone";

export type MicrophoneConfig = {
  deviceId: string;
  deviceLabel: string;
  mode: MicrophoneMode;
};
