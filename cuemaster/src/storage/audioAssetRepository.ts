export type StoredAudioAsset = {
  path: string;
  blob: Blob;
};

export const audioAssetRepository = {
  async save(_asset: StoredAudioAsset): Promise<void> {
    throw new Error("audioAssetRepository.save is not implemented");
  }
};
