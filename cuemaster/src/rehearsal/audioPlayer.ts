import { createAudioElement } from "../platform/audio";

export type AudioElementFactory = (src: string) => HTMLAudioElement;
export type AudioPlaybackState = "idle" | "playing" | "paused" | "stopped" | "failed";

export class AudioPlayer {
  private currentAudio: HTMLAudioElement | null = null;
  private state: AudioPlaybackState = "idle";

  constructor(private readonly audioElementFactory: AudioElementFactory = createAudioElement) {}

  async play(src: string, playbackRate = 1, startTimeMs = 0): Promise<void> {
    this.stop();
    const audio = this.audioElementFactory(src);
    this.currentAudio = audio;
    this.state = "playing";
    audio.playbackRate = playbackRate;
    if (startTimeMs > 0) {
      audio.currentTime = startTimeMs / 1000;
    }
    preservePitch(audio);

    try {
      await new Promise<void>((resolve, reject) => {
        audio.addEventListener("ended", () => resolve(), { once: true });
        audio.addEventListener("error", () => reject(new Error(`Audio playback failed: ${src}`)), { once: true });
        void audio.play().catch(reject);
      });
      this.state = "idle";
    } catch (error) {
      this.state = "failed";
      throw error;
    }
  }

  pause(): void {
    if (!this.currentAudio || this.state !== "playing") {
      return;
    }
    this.currentAudio.pause();
    this.state = "paused";
  }

  resume(): void {
    if (!this.currentAudio || this.state !== "paused") {
      return;
    }
    this.state = "playing";
    void this.currentAudio.play().catch(() => {
      this.state = "failed";
    });
  }

  stop(): void {
    if (!this.currentAudio) {
      return;
    }
    this.currentAudio.pause();
    this.currentAudio.removeAttribute("src");
    this.currentAudio.load();
    this.currentAudio = null;
    this.state = "stopped";
  }

  playbackState(): AudioPlaybackState {
    return this.state;
  }
}

function preservePitch(audio: HTMLAudioElement): void {
  const media = audio as HTMLAudioElement & {
    preservesPitch?: boolean;
    mozPreservesPitch?: boolean;
    webkitPreservesPitch?: boolean;
  };
  media.preservesPitch = true;
  media.mozPreservesPitch = true;
  media.webkitPreservesPitch = true;
}
