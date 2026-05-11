import { audioAssetRepository } from "../storage/audioAssetRepository";
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
  stop(): void;
};

export type AudioAssetResolver = {
  objectUrlFor(path: string): Promise<string>;
};

export class AudioQueue {
  private cancelled = false;

  constructor(
    private readonly playbookId: string,
    private readonly player: QueueAudioPlayer = new AudioPlayer(),
    private readonly assetResolver: AudioAssetResolver = new IndexedDbAudioAssetResolver(playbookId)
  ) {}

  async play(items: QueueItem[]): Promise<void> {
    this.cancelled = false;
    for (const item of items) {
      if (this.cancelled) {
        return;
      }
      if (item.kind === "delay") {
        await delay(item.durationMs);
        continue;
      }
      const url = await this.assetResolver.objectUrlFor(item.path);
      try {
        await this.player.play(url, item.playbackRate);
      } finally {
        URL.revokeObjectURL(url);
      }
    }
  }

  cancel(): void {
    this.cancelled = true;
    this.player.stop();
  }
}

function delay(durationMs: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, durationMs);
  });
}

class IndexedDbAudioAssetResolver implements AudioAssetResolver {
  constructor(private readonly playbookId: string) {}

  async objectUrlFor(path: string): Promise<string> {
    const asset = await audioAssetRepository.get(this.playbookId, path);
    if (!asset) {
      throw new Error(`Audio asset not found in local storage: ${path}. Remove and re-import this Playbook.`);
    }
    return URL.createObjectURL(asset.blob);
  }
}
