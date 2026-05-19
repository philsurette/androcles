import type { DiagramEntity, DiagramState, Point3D } from "../../staging/diagramTypes";

type BlockingDiagramProps = {
  state: DiagramState;
  iconLibrarySvg?: string | null;
};

const PADDING = 2;
const ACTOR_RADIUS = 1.35;
const PROP_RADIUS = 0.8;
const PROP_ICON_SIZE = 1.35;
const SET_PIECE_ICON_SIZE = 2.4;

export function BlockingDiagram({ state, iconLibrarySvg }: BlockingDiagramProps) {
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
      {iconLibrarySvg ? <g aria-hidden="true" dangerouslySetInnerHTML={{ __html: iconLibrarySvg }} /> : null}
      <rect className="blocking-stage" x={PADDING} y={PADDING} width={depth} height={width} />
      {state.areas?.map((area) => {
        const bounds = areaBounds(area, project);
        return (
          <g key={area.id}>
            <rect
              className="blocking-area"
              x={bounds.x}
              y={bounds.y}
              width={bounds.width}
              height={bounds.height}
            />
            <text className="blocking-area-label" x={bounds.x + 0.25} y={bounds.y + 0.75}>
              {area.id}
            </text>
          </g>
        );
      })}
      {setPieces.map((entity) => (
        <SetPiece entity={entity} key={entity.id} project={project} hasIconLibrary={Boolean(iconLibrarySvg)} />
      ))}
      {entities.map((entity) => (
        <BlockingEntity
          entity={entity}
          key={entity.id}
          project={project}
          setPieces={setPieces}
          hasIconLibrary={Boolean(iconLibrarySvg)}
        />
      ))}
    </svg>
  );

  function project(point: Point3D): { x: number; y: number } {
    return {
      x: PADDING + (depth - point.y),
      y: PADDING + (point.x + width / 2)
    };
  }
}

function areaBounds(
  area: { center: Point3D; width?: number; depth?: number },
  project: (point: Point3D) => { x: number; y: number }
): { x: number; y: number; width: number; height: number } {
  const halfWidth = (area.width ?? 0) / 2;
  const halfDepth = (area.depth ?? 0) / 2;
  const corners = [
    project({ x: area.center.x - halfWidth, y: area.center.y - halfDepth }),
    project({ x: area.center.x - halfWidth, y: area.center.y + halfDepth }),
    project({ x: area.center.x + halfWidth, y: area.center.y - halfDepth }),
    project({ x: area.center.x + halfWidth, y: area.center.y + halfDepth })
  ];
  const xs = corners.map((corner) => corner.x);
  const ys = corners.map((corner) => corner.y);
  const minX = Math.min(...xs);
  const minY = Math.min(...ys);
  return {
    x: minX,
    y: minY,
    width: Math.max(...xs) - minX,
    height: Math.max(...ys) - minY
  };
}

function SetPiece({
  entity,
  project,
  hasIconLibrary
}: {
  entity: DiagramEntity;
  project: (point: Point3D) => { x: number; y: number };
  hasIconLibrary: boolean;
}) {
  const point = entityPoint(entity);
  if (!point) {
    return null;
  }
  const projected = project(point);
  const width = entity.size?.width ?? 16;
  const depth = entity.size?.depth ?? 16;
  const href = hasIconLibrary ? iconHref(entity) : null;
  return (
    <g className="blocking-set-piece" transform={`translate(${projected.x} ${projected.y})`}>
      <title>{entity.title ?? entity.source_id ?? entity.id}</title>
      <rect x={-depth / 2} y={-width / 2} width={depth} height={width} rx="0.18" />
      {href ? (
        <use
          className="blocking-stage-icon blocking-stage-icon-set-piece"
          href={href}
          fill="none"
          stroke="currentColor"
          x={-SET_PIECE_ICON_SIZE / 2}
          y={-SET_PIECE_ICON_SIZE / 2}
          width={SET_PIECE_ICON_SIZE}
          height={SET_PIECE_ICON_SIZE}
        />
      ) : null}
    </g>
  );
}

function BlockingEntity({
  entity,
  project,
  setPieces,
  hasIconLibrary
}: {
  entity: DiagramEntity;
  project: (point: Point3D) => { x: number; y: number };
  setPieces: DiagramEntity[];
  hasIconLibrary: boolean;
}) {
  const point = entityPoint(entity);
  if (!point) {
    return null;
  }
  const projected = projectedEntityPoint(entity, project, setPieces);
  const movementFrom = entity.movement_from ? project(entity.movement_from) : null;
  const title = entity.title ?? entity.source_id ?? entity.id;
  const href = hasIconLibrary ? iconHref(entity) : null;
  return (
    <g className={`blocking-entity blocking-entity-${entity.kind}`} transform={`translate(${projected.x} ${projected.y})`}>
      <title>{title}</title>
      {movementFrom ? <MovementArrow from={{ x: movementFrom.x - projected.x, y: movementFrom.y - projected.y }} /> : null}
      {entity.kind === "actor" ? (
        <>
          <circle r={ACTOR_RADIUS} />
          <text y="0.08">{entity.label ?? entity.source_id ?? entity.id}</text>
        </>
      ) : href ? (
        <use
          className="blocking-stage-icon blocking-stage-icon-prop"
          href={href}
          fill="none"
          stroke="currentColor"
          x={-PROP_ICON_SIZE / 2}
          y={-PROP_ICON_SIZE / 2}
          width={PROP_ICON_SIZE}
          height={PROP_ICON_SIZE}
        />
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

function projectedEntityPoint(
  entity: DiagramEntity,
  project: (point: Point3D) => { x: number; y: number },
  setPieces: DiagramEntity[]
): { x: number; y: number } {
  const point = entityPoint(entity);
  if (!point) {
    return { x: 0, y: 0 };
  }
  const projected = project(point);
  const offset = entity.offset ?? {};
  if (entity.kind !== "prop") {
    return {
      x: projected.x + (offset.x ?? 0),
      y: projected.y + (offset.y ?? 0)
    };
  }
  const setPiece = setPieces.find((candidate) => candidate.source_id === entity.source || candidate.id === entity.source);
  if (!setPiece?.size) {
    return {
      x: projected.x + (offset.x ?? 0),
      y: projected.y + (offset.y ?? 0)
    };
  }
  const slotIndex = entity.slot_index ?? 0;
  const columns = [-0.28, 0, 0.28];
  const rows = [-0.24, 0.08, 0.34];
  const halfWidth = (setPiece.size.width ?? 3) / 2;
  const halfDepth = (setPiece.size.depth ?? 2) / 2;
  return {
    x: projected.x + halfDepth * columns[slotIndex % columns.length] + (offset.x ?? 0),
    y: projected.y + halfWidth * rows[Math.floor(slotIndex / columns.length) % rows.length] + (offset.y ?? 0)
  };
}

function isVisible(entity: DiagramEntity): boolean {
  return entity.visible !== false;
}

function iconHref(entity: DiagramEntity): string | null {
  return entity.icon ? `#stage-icon-${entity.icon}` : null;
}

function diagramLabel(state: DiagramState): string {
  return state.beat_id ? `Blocking diagram for scene ${state.scene_id}, beat ${state.beat_id}` : "Blocking diagram";
}
