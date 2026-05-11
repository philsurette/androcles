export class MicrophonePermissionError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "MicrophonePermissionError";
  }
}

export async function requestMicrophoneStream(): Promise<MediaStream> {
  if (!window.isSecureContext) {
    throw new MicrophonePermissionError("Microphone access requires a secure browser context.");
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new MicrophonePermissionError("No browser microphone API is available.");
  }

  try {
    return await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
  } catch (error) {
    throw new MicrophonePermissionError("Microphone permission was denied or no microphone is available.", {
      cause: error
    });
  }
}
