import { requestMicrophoneStream, stopMicrophoneStream, type MicrophoneMode } from "../platform/microphone";
import { classifyInputLevel, rootMeanSquareFloatEnergy } from "./inputMeter";
import { encodeWav } from "./wavEncoder";

export type RecordedWav = {
  blob: Blob;
  durationMs: number;
  sampleRateHz: number;
  channels: number;
};

export type WavRecorderReading = {
  energy: number;
  level: ReturnType<typeof classifyInputLevel>;
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

  constructor(
    private readonly onReading: ((reading: WavRecorderReading) => void) | null = null,
    private readonly dependencies: WavRecorderDependencies = defaultDependencies
  ) {}

  async start(deviceId: string | undefined, mode: MicrophoneMode): Promise<void> {
    this.stopWithoutResult();
    this.stream = await this.dependencies.requestStream(deviceId || undefined, mode);
    this.audioContext = this.dependencies.createAudioContext();
    if (this.audioContext.state === "suspended") {
      await this.audioContext.resume();
    }
    this.source = this.audioContext.createMediaStreamSource(this.stream);
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
    this.processor.onaudioprocess = (event) => {
      const samples = new Float32Array(event.inputBuffer.getChannelData(0));
      this.chunks.push(samples);
      if (this.onReading) {
        const energy = rootMeanSquareFloatEnergy(samples);
        this.onReading({
          energy,
          level: classifyInputLevel(energy)
        });
      }
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
