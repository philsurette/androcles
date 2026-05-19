import type { DiagramEntity, DiagramState, Point3D } from "../../staging/diagramTypes";

type BlockingDiagramProps = {
  state: DiagramState;
};

const PADDING = 2;
const ACTOR_RADIUS = 1.35;
const PROP_RADIUS = 0.8;

export function BlockingDiagram({ state }: BlockingDiagramProps) {
  const width = state.stage.width;
  const depth = state.stage.depth;
  const viewWidth = depth + PADDING * 2;
  const viewHeight = width + PADDING * 2;
  const setPieces = (state.set_pieces ?? []).filter(isVisible);
  const entities = (state.entities ?? []).filter(isVisible);

  return (
    <svg
      className="blocking-diagram"
      role="img"
      aria-label={diagramLabel(state)}
      viewBox={`0 0 ${viewWidth} ${viewHeight}`}
    >
      <title>{diagramLabel(state)}</title>
      <rect className="blocking-stage" x={PADDING} y={PADDING} width={depth} height={width} rx="2" />
      {state.areas?.map((area) => {
        const topLeft = project({ x: area.center.x - (area.width ?? 0) / 2, y: area.center.y + (area.depth ?? 0) / 2 });
        return (
          <g key={area.id}>
            <rect
              className="blocking-area"
              x={topLeft.x}
              y={topLeft.y}
              width={area.depth ?? 0}
              height={area.width ?? 0}
            />
            <text className="blocking-area-label" x={topLeft.x + 4} y={topLeft.y + 12}>
              {area.id}
            </text>
          </g>
        );
      })}
      {setPieces.map((entity) => (
        <SetPiece entity={entity} key={entity.id} project={project} />
      ))}
      {entities.map((entity) => (
        <BlockingEntity entity={entity} key={entity.id} project={project} />
      ))}
    </svg>
  );

  function project(point: Point3D): { x: number; y: number } {
    return {
      x: PADDING + (depth - point.y),
      y: PADDING + (width / 2 - point.x)
    };
  }
}

function SetPiece({ entity, project }: { entity: DiagramEntity; project: (point: Point3D) => { x: number; y: number } }) {
  const point = entityPoint(entity);
  if (!point) {
    return null;
  }
  const projected = project(point);
  const width = entity.size?.width ?? 16;
  const depth = entity.size?.depth ?? 16;
  return (
    <g className="blocking-set-piece" transform={`translate(${projected.x} ${projected.y})`}>
      <title>{entity.title ?? entity.source_id ?? entity.id}</title>
      <rect x={-depth / 2} y={-width / 2} width={depth} height={width} rx="2" />
    </g>
  );
}

function BlockingEntity({
  entity,
  project
}: {
  entity: DiagramEntity;
  project: (point: Point3D) => { x: number; y: number };
}) {
  const point = entityPoint(entity);
  if (!point) {
    return null;
  }
  const projected = project(point);
  const movementFrom = entity.movement_from ? project(entity.movement_from) : null;
  const title = entity.title ?? entity.source_id ?? entity.id;
  return (
    <g className={`blocking-entity blocking-entity-${entity.kind}`} transform={`translate(${projected.x} ${projected.y})`}>
      <title>{title}</title>
      {movementFrom ? <MovementArrow from={{ x: movementFrom.x - projected.x, y: movementFrom.y - projected.y }} /> : null}
      {entity.kind === "actor" ? (
        <>
          <circle r={ACTOR_RADIUS} />
          <text y="0.08">{entity.label ?? entity.source_id ?? entity.id}</text>
        </>
      ) : (
        <path d={`M 0 ${-PROP_RADIUS} L ${PROP_RADIUS} 0 L 0 ${PROP_RADIUS} L ${-PROP_RADIUS} 0 Z`} />
      )}
    </g>
  );
}

function MovementArrow({ from }: { from: { x: number; y: number } }) {
  const length = Math.hypot(from.x, from.y);
  if (length === 0) {
    return null;
  }
  const scale = Math.min(2.5, length) / length;
  const start = { x: from.x * scale, y: from.y * scale };
  return (
    <g className="blocking-movement-arrow">
      <line x1={start.x} y1={start.y} x2="0" y2="0" />
      <line x1="-0.55" y1="-0.55" x2="0" y2="0" transform={`rotate(${arrowRotation(start)})`} />
      <line x1="-0.55" y1="0.55" x2="0" y2="0" transform={`rotate(${arrowRotation(start)})`} />
    </g>
  );
}

function arrowRotation(start: { x: number; y: number }): number {
  return (Math.atan2(-start.y, -start.x) * 180) / Math.PI;
}

function entityPoint(entity: DiagramEntity): Point3D | null {
  return entity.point ?? entity.position ?? null;
}

function isVisible(entity: DiagramEntity): boolean {
  return entity.visible !== false;
}

function diagramLabel(state: DiagramState): string {
  return state.beat_id ? `Blocking diagram for scene ${state.scene_id}, beat ${state.beat_id}` : "Blocking diagram";
}
