export type PlaybookManifest = {
  schema_version: 1;
  format_version: string;
  package_type: "playbook";
  production: {
    source: "published" | "working";
    version?: string;
    sequence?: number;
    publication_id?: string;
    parent_version?: string;
    published_at?: string;
  };
  build: {
    buildId: string;
    buildTimestamp: string;
  };
  play: {
    id: string;
    title: string;
    authors: string[];
    source?: string;
  };
  reading: {
    type: string;
    build_type: string;
  };
  sections: ManifestSection[];
  context: ManifestContextBlock[];
  roles: ManifestRole[];
  assets: ManifestAudioAsset[];
};

export type ManifestAudioAsset = {
  path: string;
  duration_ms: number;
  required: boolean;
  cue_start_offsets?: ManifestCueStartOffset[];
};

export type ManifestCueStartOffset = {
  requested_window_ms: number;
  start_ms: number;
  confidence: "exact" | "boundary" | "fallback";
};

export type ManifestContextBlock = {
  id: string;
  part_id: number | null;
  block_id: string;
  kind: "heading" | "description" | "direction" | "blocking";
  speaker: "_NARRATOR";
  text: string;
  audio?: ManifestAudioAsset;
  content_hash: string;
  targets?: string[];
  placement?: "before" | "after";
};

export type ManifestSection = {
  id: string;
  part_id: number | null;
  block_id: string | null;
  title: string;
  ordinal: number;
};

export type ManifestRole = {
  id: string;
  display_name: string;
  reader: string;
  meta: boolean;
  parts: Array<number | null>;
  lines: ManifestLine[];
};

export type ManifestLine = {
  id: string;
  part_id: number | null;
  block_id: string;
  role: string;
  speaker: string;
  content_hash: string;
  cue: {
    speaker: string;
    text: string;
    audio: ManifestAudioAsset;
  };
  response: {
    text: string;
    segments: Array<{
      id: string;
      segment_id: string;
      content_hash: string;
      owners: string[];
      text: string;
      audio: ManifestAudioAsset;
      simultaneous?: boolean;
    }>;
  };
  directions: Array<{
    id: string;
    segment_id: string;
    content_hash: string;
    text: string;
    placement: "top_level" | "inline" | "description";
  }>;
  blocking?: Array<{
    id: string;
    segment_id: string;
    content_hash: string;
    targets: string[];
    text: string;
    placement: "top_level" | "inline" | "description";
  }>;
  previous_roles: string[];
  simultaneous?: boolean;
  timing?: {
    target_hesitation_ms?: number;
  };
};
