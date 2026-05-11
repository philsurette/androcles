import { requestMicrophoneStream, stopMicrophoneStream, type MicrophoneMode } from "../platform/microphone";
import { encodeWav } from "./wavEncoder";

export type RecordedWav = {
  blob: Blob;
  durationMs: number;
  sampleRateHz: number;
  channels: number;
};

type WavRecorderDependencies = {
  requestStream: typeof requestMicrophoneStream;
  stopStream: typeof stopMicrophoneStream;
  createAudioContext: () => AudioContext;
  now: () => number;
};

const defaultDependencies: WavRecorderDependencies = {
  requestStream: requestMicrophoneStream,
  stopStream: stopMicrophoneStream,
  createAudioContext: () => new AudioContext(),
  now: () => performance.now()
};

export class WavRecorder {
  private audioContext: AudioContext | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private processor: ScriptProcessorNode | null = null;
  private stream: MediaStream | null = null;
  private chunks: Float32Array[] = [];
  private startedAtMs = 0;

  constructor(private readonly dependencies: WavRecorderDependencies = defaultDependencies) {}

  async start(deviceId: string | undefined, mode: MicrophoneMode): Promise<void> {
    this.stopWithoutResult();
    this.stream = await this.dependencies.requestStream(deviceId || undefined, mode);
    this.audioContext = this.dependencies.createAudioContext();
    this.source = this.audioContext.createMediaStreamSource(this.stream);
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
    this.processor.onaudioprocess = (event) => {
      this.chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
    };
    this.source.connect(this.processor);
    this.processor.connect(this.audioContext.destination);
    this.startedAtMs = this.dependencies.now();
  }

  stop(): RecordedWav {
    if (!this.audioContext || !this.stream) {
      throw new Error("Recorder is not active.");
    }
    const durationMs = Math.max(0, this.dependencies.now() - this.startedAtMs);
    const sampleRateHz = this.audioContext.sampleRate;
    const blob = encodeWav({
      samples: this.chunks,
      sampleRateHz,
      channels: 1
    });
    this.stopWithoutResult();
    return {
      blob,
      durationMs,
      sampleRateHz,
      channels: 1
    };
  }

  stopWithoutResult(): void {
    if (this.processor) {
      this.processor.disconnect();
      this.processor.onaudioprocess = null;
      this.processor = null;
    }
    this.source?.disconnect();
    this.source = null;
    if (this.stream) {
      this.dependencies.stopStream(this.stream);
      this.stream = null;
    }
    void this.audioContext?.close();
    this.audioContext = null;
    this.chunks = [];
    this.startedAtMs = 0;
  }
}
