import { defaultTempoTimingConfig, type TempoTimingConfig } from "./tempoTimingConfig";

export type VoiceActivityEvent = "speech-started" | "delivery-ended";

export type VoiceActivityResult = {
  event: VoiceActivityEvent;
  atMs: number;
  hesitationMs?: number;
  deliveryMs?: number;
};

export class VoiceActivityTracker {
  private startedAtMs: number | null = null;
  private firstSpeechAtMs: number | null = null;
  private lastSpeechAtMs: number | null = null;
  private ended = false;

  constructor(private readonly config: TempoTimingConfig = defaultTempoTimingConfig) {}

  start(atMs: number): void {
    this.startedAtMs = atMs;
    this.firstSpeechAtMs = null;
    this.lastSpeechAtMs = null;
    this.ended = false;
  }

  observe(energy: number, atMs: number): VoiceActivityResult | null {
    if (this.startedAtMs === null || this.ended) {
      return null;
    }

    if (energy >= this.config.speechEnergyThreshold) {
      this.lastSpeechAtMs = atMs;
      if (this.firstSpeechAtMs === null) {
        this.firstSpeechAtMs = atMs;
        return {
          event: "speech-started",
          atMs,
          hesitationMs: atMs - this.startedAtMs
        };
      }
      return null;
    }

    if (
      this.firstSpeechAtMs !== null &&
      this.lastSpeechAtMs !== null &&
      atMs - this.lastSpeechAtMs >= this.config.endOfLineSilenceMs
    ) {
      this.ended = true;
      return {
        event: "delivery-ended",
        atMs,
        deliveryMs: this.lastSpeechAtMs - this.firstSpeechAtMs
      };
    }

    return null;
  }
}
