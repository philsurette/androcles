import type { DiagramState } from "../../staging/diagramTypes";
import { BlockingDiagram } from "./BlockingDiagram";

type BlockingDiagramSheetProps = {
  state: DiagramState;
  blockingId: string;
  noteText: string;
  onClose: () => void;
};

export function BlockingDiagramSheet({ state, blockingId, noteText, onClose }: BlockingDiagramSheetProps) {
  return (
    <div className="blocking-diagram-backdrop" role="presentation">
      <section className="blocking-diagram-sheet" role="dialog" aria-modal="true" aria-label="Blocking diagram">
        <header className="blocking-diagram-header">
          <div>
            <p className="eyebrow">{blockingId}</p>
            <h2>{noteText}</h2>
          </div>
          <button type="button" className="secondary" onClick={onClose}>
            Close
          </button>
        </header>
        <BlockingDiagram state={state} />
      </section>
    </div>
  );
}
