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
  workletUrl: string;
};

const defaultDependencies: WavRecorderDependencies = {
  requestStream: requestMicrophoneStream,
  stopStream: stopMicrophoneStream,
  createAudioContext: () => new AudioContext(),
  now: () => performance.now(),
  workletUrl: "/lineRecorderWorklet.js"
};

export class WavRecorder {
  private audioContext: AudioContext | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private processor: ScriptProcessorNode | null = null;
  private workletNode: AudioWorkletNode | null = null;
  private silentOutput: GainNode | null = null;
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
    if (await this.startAudioWorkletCapture()) {
      this.startedAtMs = this.dependencies.now();
      return;
    }
    this.startScriptProcessorCapture();
    this.startedAtMs = this.dependencies.now();
  }

  private async startAudioWorkletCapture(): Promise<boolean> {
    if (!this.audioContext?.audioWorklet || !this.source) {
      return false;
    }
    try {
      await this.audioContext.audioWorklet.addModule(this.dependencies.workletUrl);
      this.workletNode = new AudioWorkletNode(this.audioContext, "line-recorder-worklet", {
        numberOfInputs: 1,
        numberOfOutputs: 1,
        outputChannelCount: [1]
      });
      this.workletNode.port.onmessage = (event: MessageEvent<Float32Array>) => {
        this.captureSamples(event.data);
      };
      this.silentOutput = this.audioContext.createGain();
      this.silentOutput.gain.value = 0;
      this.source.connect(this.workletNode);
      this.workletNode.connect(this.silentOutput);
      this.silentOutput.connect(this.audioContext.destination);
      return true;
    } catch {
      this.workletNode?.disconnect();
      this.workletNode = null;
      this.silentOutput?.disconnect();
      this.silentOutput = null;
      return false;
    }
  }

  private startScriptProcessorCapture(): void {
    if (!this.audioContext || !this.source) {
      throw new Error("Recorder is not active.");
    }
    this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
    this.processor.onaudioprocess = (event) => {
      const samples = new Float32Array(event.inputBuffer.getChannelData(0));
      this.captureSamples(samples);
    };
    this.source.connect(this.processor);
    this.processor.connect(this.audioContext.destination);
  }

  private captureSamples(samples: Float32Array): void {
    this.chunks.push(samples);
    if (this.onReading) {
      const energy = rootMeanSquareFloatEnergy(samples);
      this.onReading({
        energy,
        level: classifyInputLevel(energy)
      });
    }
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
    if (this.workletNode) {
      this.workletNode.port.onmessage = null;
      this.workletNode.disconnect();
      this.workletNode = null;
    }
    this.silentOutput?.disconnect();
    this.silentOutput = null;
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
