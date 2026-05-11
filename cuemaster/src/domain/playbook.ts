import type { ContextBlock } from "./context";
import type { Role } from "./role";

export type Playbook = {
  id: string;
  title: string;
  authors: string[];
  source?: string;
  schemaVersion: number;
  importMetadata?: PlaybookImportMetadata;
  context: ContextBlock[];
  roles: Role[];
};

export type PlaybookImportMetadata = {
  filename: string;
  sizeBytes: number;
  importedAt: number;
};
