import type { ContextBlock } from "./context";
import type { Role } from "./role";
import type { Section } from "./section";

export type Playbook = {
  id: string;
  title: string;
  authors: string[];
  source?: string;
  schemaVersion: number;
  importMetadata?: PlaybookImportMetadata;
  sections: Section[];
  context: ContextBlock[];
  roles: Role[];
};

export type PlaybookImportMetadata = {
  filename: string;
  sizeBytes: number;
  importedAt: number;
};
