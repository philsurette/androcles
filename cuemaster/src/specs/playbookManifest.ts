export type PlaybookManifest = {
  schema_version: 1;
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
  context: ManifestContextBlock[];
  roles: ManifestRole[];
  assets: ManifestAudioAsset[];
};

export type ManifestAudioAsset = {
  path: string;
  duration_ms: number;
  required: boolean;
};

export type ManifestContextBlock = {
  id: string;
  part_id: number | null;
  block_id: string;
  kind: "heading" | "description" | "direction";
  speaker: "_NARRATOR";
  text: string;
  audio: ManifestAudioAsset;
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
  cue: {
    speaker: string;
    text: string;
    audio: ManifestAudioAsset;
  };
  response: {
    text: string;
    segments: Array<{
      id: string;
      owners: string[];
      text: string;
      audio: ManifestAudioAsset;
      simultaneous?: boolean;
    }>;
  };
  directions: Array<{
    segment_id: string;
    text: string;
    placement: "top_level" | "inline" | "description";
  }>;
  previous_roles: string[];
  simultaneous?: boolean;
  timing?: {
    target_hesitation_ms?: number;
  };
};
