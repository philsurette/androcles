import type { ContextBlock } from "./context";
import type { Role } from "./role";

export type Playbook = {
  id: string;
  title: string;
  authors: string[];
  source?: string;
  schemaVersion: number;
  context: ContextBlock[];
  roles: Role[];
};
