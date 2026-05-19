import type { DiagramState } from "../../staging/diagramTypes";
import { BlockingDiagram } from "./BlockingDiagram";

type BlockingDiagramSheetProps = {
  state: DiagramState;
  blockingId: string;
  noteText: string;
  iconLibrarySvg: string | null;
  navigationLabel?: string;
  canNavigatePrevious?: boolean;
  canNavigateNext?: boolean;
  onNavigatePrevious?: () => void;
  onNavigateNext?: () => void;
  onClose: () => void;
};

export function BlockingDiagramSheet({
  state,
  blockingId,
  noteText,
  iconLibrarySvg,
  navigationLabel,
  canNavigatePrevious = false,
  canNavigateNext = false,
  onNavigatePrevious,
  onNavigateNext,
  onClose
}: BlockingDiagramSheetProps) {
  return (
    <div className="blocking-diagram-backdrop" role="presentation">
      <section className="blocking-diagram-sheet" role="dialog" aria-modal="true" aria-label="Blocking diagram">
        <header className="blocking-diagram-header">
          <div>
            <p className="eyebrow">{blockingId}</p>
            <h2>{noteText}</h2>
            {navigationLabel ? <p className="blocking-diagram-position">{navigationLabel}</p> : null}
          </div>
          <div className="blocking-diagram-header-actions">
            <button
              type="button"
              className="quick-toggle"
              aria-label="Previous blocking diagram"
              title="Previous blocking diagram"
              onClick={onNavigatePrevious}
              disabled={!canNavigatePrevious}
            >
              <span aria-hidden="true">↤</span>
            </button>
            <button
              type="button"
              className="quick-toggle"
              aria-label="Next blocking diagram"
              title="Next blocking diagram"
              onClick={onNavigateNext}
              disabled={!canNavigateNext}
            >
              <span aria-hidden="true">↦</span>
            </button>
            <button type="button" className="quick-toggle" aria-label="Close blocking diagram" title="Close" onClick={onClose}>
              <span aria-hidden="true">×</span>
            </button>
          </div>
        </header>
        <BlockingDiagram state={state} iconLibrarySvg={iconLibrarySvg} />
      </section>
    </div>
  );
}
