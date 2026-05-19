import type { DiagramDelta, DiagramDeltaTarget, DiagramEntity, DiagramState } from "./diagramTypes";

export function applyDiagramDelta(checkpoint: DiagramState, delta: DiagramDelta, targetId?: string): DiagramState {
  const target = selectTarget(delta, targetId);
  const state = structuredClone(checkpoint);

  for (const op of target.ops) {
    if (op.op === "upsert_entity") {
      upsertEntity(state, op.entity);
    } else if (op.op === "remove_entity") {
      state.entities = removeById(state.entities, op.id);
      state.set_pieces = removeById(state.set_pieces, op.id);
    } else if (op.op === "upsert_offstage") {
      state.offstage = upsertById(state.offstage, op.entity);
    } else if (op.op === "remove_offstage") {
      state.offstage = removeById(state.offstage, op.id);
    } else if (op.op === "replace_diagnostics") {
      state.diagnostics = op.diagnostics;
    }
  }

  state.diagram_id = target.target_id;
  state.diagram_kind = "beat";
  state.scene_id = target.scene_id ?? state.scene_id;
  state.beat_id = target.beat_id ?? state.beat_id;
  return state;
}

function selectTarget(delta: DiagramDelta, targetId?: string): DiagramDeltaTarget {
  if (targetId) {
    const target = delta.targets.find((candidate) => candidate.target_id === targetId);
    if (!target) {
      throw new Error(`Blocking diagram delta does not contain target ${targetId}`);
    }
    return target;
  }
  const target = delta.targets[0];
  if (!target) {
    throw new Error("Blocking diagram delta has no targets");
  }
  return target;
}

function upsertEntity(state: DiagramState, entity: DiagramEntity): void {
  if (entity.kind === "set_piece" || entity.layer === "set" || entity.id.startsWith("set_piece:")) {
    state.set_pieces = upsertById(state.set_pieces, entity);
  } else {
    state.entities = upsertById(state.entities, entity);
  }
}

function upsertById(entities: DiagramEntity[] | undefined, entity: DiagramEntity): DiagramEntity[] {
  const next = [...(entities ?? [])];
  const index = next.findIndex((candidate) => candidate.id === entity.id);
  if (index >= 0) {
    next[index] = entity;
  } else {
    next.push(entity);
  }
  return next;
}

function removeById(entities: DiagramEntity[] | undefined, id: string): DiagramEntity[] {
  return (entities ?? []).filter((entity) => entity.id !== id);
}
