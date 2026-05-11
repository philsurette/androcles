import { db } from "./db";
import type { AudioAssetRepository } from "./storage";

export type StoredAudioAsset = {
  playbookId: string;
  path: string;
  blob: Blob;
};

export const audioAssetRepository: AudioAssetRepository = {
  save: (asset: StoredAudioAsset) => db.audioAssets.put(asset),
  get: (playbookId: string, path: string) => db.audioAssets.get([playbookId, path]),
  deleteForPlaybook: (playbookId: string) => db.audioAssets.where("playbookId").equals(playbookId).delete()
};
