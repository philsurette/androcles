import type { BlockingNote, Line } from "../domain/line";
import type { DiagramBundleManifest } from "../staging/diagramTypes";
import { resolveDiagramTarget } from "../staging/diagramResolver";

export type BlockingNavigationScope =
  | { mode: "all" }
  | { mode: "role"; roleId: string };

export type BlockingNavigationItem = {
  line: Line;
  blocking: BlockingNote;
};

export function buildBlockingNavigationItems(
  lines: Line[],
  scope: BlockingNavigationScope,
  manifest: DiagramBundleManifest | null
): BlockingNavigationItem[] {
  const items: BlockingNavigationItem[] = [];
  for (const line of lines) {
    for (const blocking of line.blocking ?? []) {
      if (!isInScope(blocking, scope)) {
        continue;
      }
      if (manifest && resolveDiagramTarget(manifest, line.id, blocking.id) === null) {
        continue;
      }
      items.push({ line, blocking });
    }
  }
  return items;
}

export function blockingNavigationIndex(
  items: BlockingNavigationItem[],
  lineId: string,
  blockingId: string
): number {
  return items.findIndex((item) => item.line.id === lineId && item.blocking.id === blockingId);
}

function isInScope(blocking: BlockingNote, scope: BlockingNavigationScope): boolean {
  if (scope.mode === "all") {
    return true;
  }
  return blocking.targets.includes("*") || blocking.targets.includes(scope.roleId);
}
