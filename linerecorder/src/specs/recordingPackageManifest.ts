export type RecordingRequestManifest = {
  schema_version: 1;
  package_type: "recording_request";
  request: {
    id: string;
    kind: "full_role" | "selected_segments" | "rerecord";
    created_at: string;
    created_by: string;
    notes?: string;
  };
  play: {
    id: string;
    title: string;
    version?: string;
  };
  role: {
    id: string;
    display_name: string;
  };
  recording: {
    preferred_sample_rate_hz: number;
    preferred_channels: number;
    source_format: "wav";
  };
  items: RecordingRequestItemManifest[];
};

export type RecordingRequestItemManifest = {
  id: string;
  line_id: string;
  block_id: string;
  segment_id: string;
  line_content_hash?: string;
  segment_content_hash?: string;
  sequence: number;
  display_text: string;
  segment_text: string;
  output_path: string;
  cue_text?: string;
  cue_speaker?: string;
  previous_text?: string;
  previous_speaker?: string;
  next_text?: string;
  next_speaker?: string;
  section_id?: string;
  section_title?: string;
  scene_heading?: string;
  stage_directions?: string[];
  reason?: string;
  notes?: string;
  previous_recording?: string;
  cue_audio?: string;
  changed?: boolean;
  target_duration_ms?: number;
  target_hesitation_ms?: number;
  simultaneous?: boolean;
};

export type RoleRecordingsManifest = {
  schema_version: 1;
  package_type: "role_recordings";
  complete: boolean;
  play: {
    id: string;
    title: string;
    version?: string;
  };
  role: {
    id: string;
    display_name: string;
  };
  recordings: RoleRecordingManifestItem[];
  missing_segment_ids: string[];
};

export type RoleRecordingManifestItem = {
  id: string;
  line_id: string;
  block_id: string;
  segment_id: string;
  line_content_hash?: string;
  segment_content_hash?: string;
  audio_path: string;
  recorded_at: string;
  duration_ms: number;
  sample_rate_hz: number;
  channels: number;
  input_quality?: {
    peak_energy: number;
    level_counts: {
      no_signal: number;
      too_quiet: number;
      good: number;
      clipping: number;
    };
  };
  status: "accepted";
};
