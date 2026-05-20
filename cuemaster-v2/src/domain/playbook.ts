export type Playbook = {
  id: string;
  title: string;
  authors: string[];
  formatVersion: string;
  buildTimestamp: string;
  productionSource: "published" | "working";
  staging?: {
    format: "quince.blocking.diagram_bundle";
    formatVersion: string;
    manifestPath: string;
  };
  sections: PlaybookSection[];
  context: PlaybookContextBlock[];
  roles: PlaybookRole[];
};

export type PlaybookSection = {
  id: string;
  partId: number | null;
  blockId: string | null;
  title: string;
  ordinal: number;
};

export type PlaybookContextBlock = {
  id: string;
  partId: number | null;
  blockId: string;
  kind: "heading" | "description" | "direction" | "blocking";
  speaker: string;
  text: string;
  audioPath?: string;
  durationMs?: number;
  targets?: string[];
  placement?: "before" | "after";
};

export type PlaybookRole = {
  id: string;
  displayName: string;
  lineCount: number;
  lines: PlaybookLine[];
};

export type PlaybookLine = {
  id: string;
  partId: number | null;
  blockId: string;
  role: string;
  speaker: string;
  cue: PlaybookCue;
  responseText: string;
  responseSegments: PlaybookResponseSegment[];
  directions: PlaybookDirection[];
  blocking: PlaybookBlockingNote[];
  previousRoles: string[];
};

export type PlaybookCue = {
  speaker: string;
  text: string;
  audioPath: string;
  durationMs: number;
};

export type PlaybookResponseSegment = {
  id: string;
  segmentId: string;
  owners: string[];
  text: string;
  audioPath: string;
  durationMs: number;
  simultaneous: boolean;
};

export type PlaybookDirection = {
  id: string;
  segmentId: string;
  text: string;
  placement: "top_level" | "inline" | "description";
};

export type PlaybookBlockingNote = {
  id: string;
  segmentId?: string;
  targets: string[];
  text: string;
  placement: "before" | "after" | "top_level" | "inline" | "description";
};

export type LoadedPlaybook = {
  playbook: Playbook;
  audioAssets: Map<string, Blob>;
};
