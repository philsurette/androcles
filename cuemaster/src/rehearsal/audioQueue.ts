import { audioAssetRepository } from "../storage/audioAssetRepository";
import { AudioPlayer } from "./audioPlayer";

export type AudioQueueItem = {
  path: string;
  playbackRate: number;
};

export class AudioQueue {
  private cancelled = false;

  constructor(
    private readonly playbookId: string,
    private readonly player = new AudioPlayer()
  ) {}

  async play(items: AudioQueueItem[]): Promise<void> {
    this.cancelled = false;
    for (const item of items) {
      if (this.cancelled) {
        return;
      }
      const url = await this.objectUrlFor(item.path);
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

  private async objectUrlFor(path: string): Promise<string> {
    const asset = await audioAssetRepository.get(this.playbookId, path);
    if (!asset) {
      throw new Error(`Audio asset not found: ${path}`);
    }
    return URL.createObjectURL(asset.blob);
  }
}
