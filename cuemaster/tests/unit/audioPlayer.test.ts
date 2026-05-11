import { describe, expect, it, vi } from "vitest";
import { AudioPlayer } from "../../src/rehearsal/audioPlayer";

describe("AudioPlayer", () => {
  it("pauses active playback without completing playback", async () => {
    const audio = new FakeAudioElement();
    const player = new AudioPlayer(() => audio.element());
    const playback = player.play("blob://line.wav");

    await Promise.resolve();
    player.pause();

    expect(audio.pause).toHaveBeenCalledOnce();
    expect(player.playbackState()).toBe("paused");
    expect(audio.removeAttribute).not.toHaveBeenCalled();

    audio.dispatch("ended");
    await playback;

    expect(player.playbackState()).toBe("idle");
  });

  it("ignores pause when playback is not active", () => {
    const audio = new FakeAudioElement();
    const player = new AudioPlayer(() => audio.element());

    player.pause();

    expect(audio.pause).not.toHaveBeenCalled();
    expect(player.playbackState()).toBe("idle");
  });

  it("resumes paused playback", async () => {
    const audio = new FakeAudioElement();
    const player = new AudioPlayer(() => audio.element());
    const playback = player.play("blob://line.wav");

    await Promise.resolve();
    player.pause();
    player.resume();

    expect(audio.play).toHaveBeenCalledTimes(2);
    expect(player.playbackState()).toBe("playing");

    audio.dispatch("ended");
    await playback;
  });

  it("starts playback from a requested content offset", async () => {
    const audio = new FakeAudioElement();
    const player = new AudioPlayer(() => audio.element());
    const playback = player.play("blob://cue.wav", 1, 12500);

    await Promise.resolve();

    expect(audio.currentTime).toBe(12.5);

    audio.dispatch("ended");
    await playback;
  });
});

class FakeAudioElement {
  readonly pause = vi.fn();
  readonly play = vi.fn(async () => undefined);
  readonly load = vi.fn();
  readonly removeAttribute = vi.fn();
  currentTime = 0;
  playbackRate = 1;
  preservesPitch?: boolean;
  mozPreservesPitch?: boolean;
  webkitPreservesPitch?: boolean;
  private readonly listeners = new Map<string, Array<() => void>>();

  addEventListener(event: string, listener: () => void): void {
    this.listeners.set(event, [...(this.listeners.get(event) ?? []), listener]);
  }

  dispatch(event: string): void {
    for (const listener of this.listeners.get(event) ?? []) {
      listener();
    }
  }

  element(): HTMLAudioElement {
    return this as unknown as HTMLAudioElement;
  }
}
