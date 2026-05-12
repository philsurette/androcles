import { classifyInputLevel, rootMeanSquareEnergy, smoothMeterEnergy, type InputLevel } from "./inputMeter";
import { requestMicrophoneStream, stopMicrophoneStream, type MicrophoneMode } from "../platform/microphone";

export type MicrophoneReading = {
  energy: number;
  level: InputLevel;
};

type MicrophoneSessionDependencies = {
  requestStream: typeof requestMicrophoneStream;
  stopStream: typeof stopMicrophoneStream;
  createAudioContext: () => AudioContext;
  requestFrame: (callback: FrameRequestCallback) => number;
  cancelFrame: (id: number) => void;
};

const defaultDependencies: MicrophoneSessionDependencies = {
  requestStream: requestMicrophoneStream,
  stopStream: stopMicrophoneStream,
  createAudioContext: () => new AudioContext(),
  requestFrame: (callback) => requestAnimationFrame(callback),
  cancelFrame: (id) => cancelAnimationFrame(id)
};

export class MicrophoneSession {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private stream: MediaStream | null = null;
  private frameId: number | null = null;
  private samples: Uint8Array<ArrayBuffer> | null = null;
  private displayedEnergy = 0;

  constructor(
    private readonly onReading: (reading: MicrophoneReading) => void,
    private readonly dependencies: MicrophoneSessionDependencies = defaultDependencies
  ) {}

  async start(deviceId: string | undefined, mode: MicrophoneMode): Promise<void> {
    this.stop();
    this.stream = await this.dependencies.requestStream(deviceId || undefined, mode);
    this.audioContext = this.dependencies.createAudioContext();
    const source = this.audioContext.createMediaStreamSource(this.stream);
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 1024;
    this.samples = new Uint8Array(this.analyser.fftSize);
    source.connect(this.analyser);
    this.read();
  }

  stop(): void {
    if (this.frameId !== null) {
      this.dependencies.cancelFrame(this.frameId);
      this.frameId = null;
    }
    if (this.stream) {
      this.dependencies.stopStream(this.stream);
      this.stream = null;
    }
    void this.audioContext?.close();
    this.audioContext = null;
    this.analyser = null;
    this.samples = null;
    this.displayedEnergy = 0;
  }

  private read(): void {
    if (!this.analyser || !this.samples) {
      return;
    }
    this.analyser.getByteTimeDomainData(this.samples);
    const energy = rootMeanSquareEnergy(this.samples);
    this.displayedEnergy = smoothMeterEnergy(this.displayedEnergy, energy);
    this.onReading({
      energy: this.displayedEnergy,
      level: classifyInputLevel(this.displayedEnergy)
    });
    this.frameId = this.dependencies.requestFrame(() => this.read());
  }
}
