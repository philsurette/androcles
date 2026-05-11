import { indexedDbStorage } from "../storage/indexedDbStorage";
import { AudioPlayer } from "./audioPlayer";

export type AudioQueueItem = {
  kind: "audio";
  path: string;
  playbackRate: number;
};

export type DelayQueueItem = {
  kind: "delay";
  durationMs: number;
};

export type QueueItem = AudioQueueItem | DelayQueueItem;

export type QueueAudioPlayer = {
  play(src: string, playbackRate: number): Promise<void>;
  pause(): void;
  resume(): void;
  stop(): void;
};

export type AudioAssetResolver = {
  objectUrlFor(path: string): Promise<string>;
};

export class AudioQueue {
  private cancelled = false;
  private paused = false;
  private readonly pauseListeners = new Set<() => void>();

  constructor(
    private readonly playbookId: string,
    private readonly player: QueueAudioPlayer = new AudioPlayer(),
    private readonly assetResolver: AudioAssetResolver = new IndexedDbAudioAssetResolver(playbookId)
  ) {}

  async play(items: QueueItem[]): Promise<void> {
    this.cancelled = false;
    this.paused = false;
    for (const item of items) {
      if (this.cancelled) {
        return;
      }
      if (item.kind === "delay") {
        await this.delay(item.durationMs);
        continue;
      }
      await this.waitIfPaused();
      const url = await this.assetResolver.objectUrlFor(item.path);
      try {
        await this.player.play(url, item.playbackRate);
      } finally {
        URL.revokeObjectURL(url);
      }
    }
  }

  pause(): void {
    if (this.paused) {
      return;
    }
    this.paused = true;
    this.player.pause();
  }

  resume(): void {
    if (!this.paused) {
      return;
    }
    this.paused = false;
    this.player.resume();
    for (const listener of this.pauseListeners) {
      listener();
    }
    this.pauseListeners.clear();
  }

  cancel(): void {
    this.cancelled = true;
    this.paused = false;
    for (const listener of this.pauseListeners) {
      listener();
    }
    this.pauseListeners.clear();
    this.player.stop();
  }

  private async delay(durationMs: number): Promise<void> {
    let remainingMs = durationMs;
    while (remainingMs > 0 && !this.cancelled) {
      await this.waitIfPaused();
      const delayMs = Math.min(remainingMs, delaySliceMs);
      await delay(delayMs);
      remainingMs -= delayMs;
    }
  }

  private waitIfPaused(): Promise<void> {
    if (!this.paused || this.cancelled) {
      return Promise.resolve();
    }
    return new Promise((resolve) => {
      this.pauseListeners.add(resolve);
    });
  }
}

function delay(durationMs: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, durationMs);
  });
}

const delaySliceMs = 50;

class IndexedDbAudioAssetResolver implements AudioAssetResolver {
  constructor(private readonly playbookId: string) {}

  async objectUrlFor(path: string): Promise<string> {
    const asset = await indexedDbStorage.audioAssets.get(this.playbookId, path);
    if (!asset) {
      throw new Error(`Audio asset not found in local storage: ${path}. Remove and re-import this Playbook.`);
    }
    return URL.createObjectURL(asset.blob);
  }
}
