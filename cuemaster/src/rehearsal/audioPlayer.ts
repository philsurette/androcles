import { createAudioElement } from "../platform/audio";

export class AudioPlayer {
  private currentAudio: HTMLAudioElement | null = null;

  async play(src: string, playbackRate = 1): Promise<void> {
    this.stop();
    const audio = createAudioElement(src);
    this.currentAudio = audio;
    audio.playbackRate = playbackRate;
    preservePitch(audio);

    await new Promise<void>((resolve, reject) => {
      audio.addEventListener("ended", () => resolve(), { once: true });
      audio.addEventListener("error", () => reject(new Error(`Audio playback failed: ${src}`)), { once: true });
      void audio.play().catch(reject);
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
