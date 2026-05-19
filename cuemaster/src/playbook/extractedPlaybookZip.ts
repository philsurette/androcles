import type { PlaybookManifest } from "../specs/playbookManifest";
import { PlaybookAssetIndex } from "./playbookAssetIndex";

export type ExtractedAudioAsset = {
  path: string;
  blob: Blob;
};

export type ExtractedJsonAsset = {
  path: string;
  text: string;
};

export type ExtractedPlaybookZip = {
  manifest: PlaybookManifest;
  assetIndex: PlaybookAssetIndex;
  audioAssets: ExtractedAudioAsset[];
  jsonAssets: ExtractedJsonAsset[];
};

export type ExtractedPlaybookZipData = {
  manifest: PlaybookManifest;
  manifestJson: string;
  assetPaths: string[];
  audioAssets: ExtractedAudioAsset[];
  jsonAssets: ExtractedJsonAsset[];
};
