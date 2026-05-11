import type { PlaybookManifest } from "../specs/playbookManifest";
import { PlaybookAssetIndex } from "./playbookAssetIndex";

export type ExtractedAudioAsset = {
  path: string;
  blob: Blob;
};

export type ExtractedPlaybookZip = {
  manifest: PlaybookManifest;
  assetIndex: PlaybookAssetIndex;
  audioAssets: ExtractedAudioAsset[];
};

export type ExtractedPlaybookZipData = {
  manifest: PlaybookManifest;
  assetPaths: string[];
  audioAssets: ExtractedAudioAsset[];
};

