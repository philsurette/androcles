import type { ContextBlock } from "./context";
import type { Role } from "./role";
import type { Section } from "./section";

export type Playbook = {
  id: string;
  title: string;
  authors: string[];
  audioAssetPaths?: string[];
  manifestText?: string;
  build?: PlaybookBuild;
  production: PlaybookProduction;
  source?: string;
  schemaVersion: number;
  importMetadata?: PlaybookImportMetadata;
  sections: Section[];
  context: ContextBlock[];
  roles: Role[];
};

export type PlaybookBuild = {
  buildId: string;
  buildTimestamp: string;
};

export type PlaybookProduction = {
  source: "published" | "working";
  version?: string;
  sequence?: number;
  publicationId?: string;
  parentVersion?: string;
  publishedAt?: string;
  changeSummary?: string;
  blockingChanges?: string[];
};

export type PlaybookImportMetadata = {
  filename: string;
  sizeBytes: number;
  importedAt: number;
};
