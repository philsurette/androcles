import { db } from "./db";

export type StoredAudioAsset = {
  playbookId: string;
  path: string;
  blob: Blob;
};

export const audioAssetRepository = {
  save: (asset: StoredAudioAsset) => db.audioAssets.put(asset),
  get: (playbookId: string, path: string) => db.audioAssets.get([playbookId, path]),
  deleteForPlaybook: (playbookId: string) => db.audioAssets.where("playbookId").equals(playbookId).delete()
};
