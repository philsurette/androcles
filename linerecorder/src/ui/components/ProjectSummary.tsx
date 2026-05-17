import type { RecordingItemProgress } from "../../domain/recordingItemStatus";
import type { RecordingProjectRecord } from "../../storage/db";

type ProjectSummaryProps = {
  project: RecordingProjectRecord;
  progress: RecordingItemProgress[];
  onExport: () => void;
  onViewInfo: () => void;
  onBack: () => void;
  isExplorerOpen: boolean;
  onToggleExplorer: () => void;
  isExporting: boolean;
};

export function ProjectSummary({
  project,
  progress,
  onExport,
  onViewInfo,
  onBack,
  isExplorerOpen,
  onToggleExplorer,
  isExporting
}: ProjectSummaryProps) {
  const acceptedCount = progress.filter((candidate) => candidate.status === "accepted").length;
  return (
    <article className="summary-panel">
      <div className="summary-title">
        <div className="summary-title-main">
          <button type="button" className="secondary icon-button summary-back-button" onClick={onBack}>
            <span aria-hidden="true">←</span>
            <span className="visually-hidden">Back</span>
          </button>
          <div className="summary-title-text">
            <p className="eyebrow">{project.request.play.title}</p>
            <h2>{project.request.role.displayName}</h2>
          </div>
        </div>
        <div className="summary-title-actions">
          <button
            type="button"
            className="secondary summary-action-icon"
            aria-label={isExporting ? "Export disabled" : "Export recordings"}
            disabled={acceptedCount === 0 || isExporting}
            onClick={onExport}
          >
            <span aria-hidden="true">⬇</span>
            <span className="visually-hidden">{isExporting ? "Exporting recordings" : "Export recordings"}</span>
          </button>
          <button
            type="button"
            className="secondary summary-action-icon summary-lines-toggle"
            aria-label={isExplorerOpen ? "Hide line list" : "Show line list"}
            title={isExplorerOpen ? "Hide line list" : "Show line list"}
            onClick={onToggleExplorer}
          >
            <span aria-hidden="true">📋</span>
            <span className="visually-hidden">{isExplorerOpen ? "Hide line list" : "Show line list"}</span>
          </button>
          <button type="button" className="secondary summary-action-icon" onClick={onViewInfo} aria-label="Project info">
            <span aria-hidden="true">ⓘ</span>
            <span className="visually-hidden">Project information</span>
          </button>
        </div>
      </div>
      <div className="summary-compact-meta">{acceptedCount}/{progress.length} accepted</div>
      {project.request.request.notes ? <p className="notes">{project.request.request.notes}</p> : null}
    </article>
  );
}
