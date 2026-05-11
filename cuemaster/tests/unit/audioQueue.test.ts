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
      { kind: "audio", path: "cue.wav", playbackRate: 1 },
      { kind: "audio", path: "response.wav", playbackRate: 0.7 }
    ]);

    expect(player.playCalls).toEqual([
      ["blob://cue.wav", 1, undefined],
      ["blob://response.wav", 0.7, undefined]
    ]);
    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(2);
  });

  it("cancels playback and stops the active player", async () => {
    let queue: AudioQueue;
    const player = new MockAudioPlayer(() => queue.cancel());
    queue = new AudioQueue("playbook", player, new MockAssetResolver());

    await queue.play([
      { kind: "audio", path: "cue.wav", playbackRate: 1 },
      { kind: "audio", path: "response.wav", playbackRate: 0.7 }
    ]);

    expect(player.stop).toHaveBeenCalledOnce();
    expect(player.playCalls).toEqual([["blob://cue.wav", 1, undefined]]);
    expect(URL.revokeObjectURL).toHaveBeenCalledOnce();
  });

  it("pauses and resumes the active player", () => {
    const player = new MockAudioPlayer();
    const queue = new AudioQueue("playbook", player, new MockAssetResolver());

    queue.pause();
    queue.resume();

    expect(player.pause).toHaveBeenCalledOnce();
    expect(player.resume).toHaveBeenCalledOnce();
  });

  it("waits for delay items without resolving audio assets", async () => {
    vi.useFakeTimers();
    const player = new MockAudioPlayer();
    const resolver = new MockAssetResolver();
    const queue = new AudioQueue("playbook", player, resolver);

    const promise = queue.play([
      { kind: "delay", durationMs: 750 },
      { kind: "audio", path: "response.wav", playbackRate: 0.8 }
    ]);

    await vi.advanceTimersByTimeAsync(749);
    expect(player.playCalls).toEqual([]);
    await vi.advanceTimersByTimeAsync(1);
    await promise;

    expect(resolver.paths).toEqual(["response.wav"]);
    expect(player.playCalls).toEqual([["blob://response.wav", 0.8, undefined]]);
    vi.useRealTimers();
  });

  it("passes audio start times to the player", async () => {
    const player = new MockAudioPlayer();
    const queue = new AudioQueue("playbook", player, new MockAssetResolver());

    await queue.play([{ kind: "audio", path: "cue.wav", playbackRate: 1, startTimeMs: 20000 }]);

    expect(player.playCalls).toEqual([["blob://cue.wav", 1, 20000]]);
  });
});

class MockAudioPlayer implements QueueAudioPlayer {
  readonly playCalls: Array<[string, number, number | undefined]> = [];
  readonly pause = vi.fn();
  readonly resume = vi.fn();
  readonly stop = vi.fn();

  constructor(private readonly onPlay?: () => void) {}

  async play(src: string, playbackRate: number, startTimeMs?: number): Promise<void> {
    this.playCalls.push([src, playbackRate, startTimeMs]);
    this.onPlay?.();
  }
}

class MockAssetResolver implements AudioAssetResolver {
  readonly paths: string[] = [];

  async objectUrlFor(path: string): Promise<string> {
    this.paths.push(path);
    return `blob://${path}`;
  }
}
