import { db } from "./db";
import type { JsonAssetRepository } from "./storage";

export type StoredJsonAsset = {
  playbookId: string;
  path: string;
  text: string;
};

export const jsonAssetRepository: JsonAssetRepository = {
  save: (asset: StoredJsonAsset) => db.jsonAssets.put(asset),
  get: (playbookId: string, path: string) => db.jsonAssets.get([playbookId, path]),
  deleteForPlaybook: (playbookId: string) => db.jsonAssets.where("playbookId").equals(playbookId).delete()
};
