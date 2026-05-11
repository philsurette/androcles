export type MicrophoneDevice = {
  deviceId: string;
  label: string;
};

export type MicrophoneMode = "clean" | "noisy";

export class MicrophonePermissionError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "MicrophonePermissionError";
  }
}

export async function listMicrophoneDevices(): Promise<MicrophoneDevice[]> {
  assertMicrophoneApiAvailable();
  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices
    .filter((device) => device.kind === "audioinput")
    .map((device, index) => ({
      deviceId: device.deviceId,
      label: device.label || `Microphone ${index + 1}`
    }));
}

export async function requestMicrophoneStream(deviceId?: string, mode: MicrophoneMode = "clean"): Promise<MediaStream> {
  assertMicrophoneApiAvailable();
  try {
    return await navigator.mediaDevices.getUserMedia({
      audio: microphoneConstraints(deviceId, mode),
      video: false
    });
  } catch (error) {
    throw new MicrophonePermissionError("Microphone permission was denied or no microphone is available.", {
      cause: error
    });
  }
}

export function stopMicrophoneStream(stream: MediaStream): void {
  stream.getTracks().forEach((track) => track.stop());
}

function assertMicrophoneApiAvailable(): void {
  if (!window.isSecureContext) {
    throw new MicrophonePermissionError("Microphone access requires a secure browser context.");
  }
  if (!navigator.mediaDevices?.getUserMedia || !navigator.mediaDevices.enumerateDevices) {
    throw new MicrophonePermissionError("No browser microphone API is available.");
  }
}

function microphoneConstraints(deviceId: string | undefined, mode: MicrophoneMode): MediaTrackConstraints {
  return {
    deviceId: deviceId ? { exact: deviceId } : undefined,
    channelCount: 1,
    echoCancellation: mode === "noisy",
    noiseSuppression: mode === "noisy",
    autoGainControl: mode === "noisy"
  };
}
