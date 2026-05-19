export type Point3D = {
  x: number;
  y: number;
  z?: number;
};

export type DiagramBundleManifest = {
  format: "quince.blocking.diagram_bundle";
  format_version: string;
  default_orientation?: "portrait" | "landscape";
  checkpoints: DiagramCheckpointRecord[];
  deltas: DiagramDeltaRecord[];
};

export type DiagramCheckpointRecord = {
  id: string;
  scene_id?: string;
  set_id?: string;
  path: string;
};

export type DiagramDeltaRecord = {
  id: string;
  scene_id?: string;
  beat_id?: string;
  production_anchor?: string;
  from_checkpoint: string;
  path: string;
};

export type DiagramStage = {
  type?: string;
  width: number;
  depth: number;
  units?: string;
  audience?: string;
  measured?: boolean;
};

export type DiagramArea = {
  id: string;
  center: Point3D;
  width?: number;
  depth?: number;
  aliases?: string[];
};

export type DiagramEntity = {
  id: string;
  source_id?: string;
  kind: string;
  layer?: string;
  source?: string;
  title?: string;
  label?: string;
  visible?: boolean;
  elevation?: number;
  fixed?: boolean;
  movable?: boolean;
  point?: Point3D;
  position?: Point3D;
  size?: { width?: number; depth?: number; radius?: number };
  icon?: string;
  face?: string;
  movement_from?: Point3D;
  movement_to?: Point3D;
};

export type DiagramState = {
  format: "quince.blocking.diagram_state";
  format_version: string;
  diagram_id: string;
  diagram_kind?: string;
  scene_id?: string;
  beat_id?: string;
  set_id?: string;
  stage: DiagramStage;
  areas?: DiagramArea[];
  levels?: unknown[];
  connectors?: unknown[];
  anchors?: unknown[];
  set_pieces?: DiagramEntity[];
  entities?: DiagramEntity[];
  offstage?: DiagramEntity[];
  diagnostics?: string[];
};

export type DiagramDelta = {
  format: "quince.blocking.diagram_delta";
  format_version: string;
  from_checkpoint: string;
  targets: DiagramDeltaTarget[];
};

export type DiagramDeltaTarget = {
  target_id: string;
  scene_id?: string;
  beat_id?: string;
  production_anchor?: string;
  ops: DiagramDeltaOp[];
};

export type DiagramDeltaOp =
  | { op: "upsert_entity"; entity: DiagramEntity }
  | { op: "remove_entity"; id: string }
  | { op: "upsert_offstage"; entity: DiagramEntity }
  | { op: "remove_offstage"; id: string }
  | { op: "replace_diagnostics"; diagnostics: string[] };
