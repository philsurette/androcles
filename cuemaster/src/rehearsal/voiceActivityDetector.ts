import { requestMicrophoneStream } from "../platform/microphone";
import { defaultTempoTimingConfig, type TempoTimingConfig } from "./tempoTimingConfig";
import { VoiceActivityTracker, type VoiceActivityResult } from "./voiceActivityTracker";

export class VoiceActivityDetector {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private stream: MediaStream | null = null;
  private animationFrameId: number | null = null;
  private readonly tracker: VoiceActivityTracker;

  constructor(
    private readonly onActivity: (result: VoiceActivityResult) => void,
    config: TempoTimingConfig = defaultTempoTimingConfig
  ) {
    this.tracker = new VoiceActivityTracker(config);
  }

  async start(): Promise<void> {
    this.stop();
    this.stream = await requestMicrophoneStream();
    this.audioContext = new AudioContext();
    const source = this.audioContext.createMediaStreamSource(this.stream);
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 1024;
    source.connect(this.analyser);
    this.tracker.start(performance.now());
    this.readEnergy();
  }

  stop(): void {
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
    void this.audioContext?.close();
    this.audioContext = null;
    this.analyser = null;
  }

  private readEnergy(): void {
    if (!this.analyser) {
      return;
    }

    const samples = new Uint8Array(this.analyser.fftSize);
    this.analyser.getByteTimeDomainData(samples);
    const energy = rootMeanSquareEnergy(samples);
    const result = this.tracker.observe(energy, performance.now());
    if (result) {
      this.onActivity(result);
    }
    this.animationFrameId = requestAnimationFrame(() => this.readEnergy());
  }
}

export function rootMeanSquareEnergy(samples: Uint8Array): number {
  let sum = 0;
  for (const sample of samples) {
    const normalized = (sample - 128) / 128;
    sum += normalized * normalized;
  }
  return Math.sqrt(sum / samples.length);
}
