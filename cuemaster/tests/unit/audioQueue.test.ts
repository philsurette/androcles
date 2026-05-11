import { beforeEach, describe, expect, it, vi } from "vitest";
import { AudioQueue, type AudioAssetResolver, type QueueAudioPlayer } from "../../src/rehearsal/audioQueue";

describe("AudioQueue", () => {
  beforeEach(() => {
    URL.revokeObjectURL = vi.fn();
  });

  it("plays queued assets sequentially at the requested speeds", async () => {
    const player = new MockAudioPlayer();
    const queue = new AudioQueue("playbook", player, new MockAssetResolver());

    await queue.play([
      { path: "cue.wav", playbackRate: 1 },
      { path: "response.wav", playbackRate: 0.7 }
    ]);

    expect(player.playCalls).toEqual([
      ["blob://cue.wav", 1],
      ["blob://response.wav", 0.7]
    ]);
    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(2);
  });

  it("cancels playback and stops the active player", async () => {
    let queue: AudioQueue;
    const player = new MockAudioPlayer(() => queue.cancel());
    queue = new AudioQueue("playbook", player, new MockAssetResolver());

    await queue.play([
      { path: "cue.wav", playbackRate: 1 },
      { path: "response.wav", playbackRate: 0.7 }
    ]);

    expect(player.stop).toHaveBeenCalledOnce();
    expect(player.playCalls).toEqual([["blob://cue.wav", 1]]);
    expect(URL.revokeObjectURL).toHaveBeenCalledOnce();
  });
});

class MockAudioPlayer implements QueueAudioPlayer {
  readonly playCalls: Array<[string, number]> = [];
  readonly stop = vi.fn();

  constructor(private readonly onPlay?: () => void) {}

  async play(src: string, playbackRate: number): Promise<void> {
    this.playCalls.push([src, playbackRate]);
    this.onPlay?.();
  }
}

class MockAssetResolver implements AudioAssetResolver {
  async objectUrlFor(path: string): Promise<string> {
    return `blob://${path}`;
  }
}
