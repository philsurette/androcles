export type RoleRecordingPackManifest = {
  schema_version: 1;
  package_type: "role_recording_pack";
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
  items: RoleRecordingPackItemManifest[];
};

export type RoleRecordingPackItemManifest = {
  line_id: string;
  block_id: string;
  segment_id: string;
  sequence: number;
  display_text: string;
  segment_text: string;
  output_path: string;
  cue_text?: string;
  section_id?: string;
  section_title?: string;
  scene_heading?: string;
  stage_directions?: string[];
  notes?: string;
  previous_recording?: string;
  changed?: boolean;
  target_duration_ms?: number;
  target_hesitation_ms?: number;
  simultaneous?: boolean;
};
