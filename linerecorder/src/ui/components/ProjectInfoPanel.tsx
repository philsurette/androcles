import type { RecordingItem } from "../../domain/recordingItem";
import type { RecordingProjectRecord } from "../../storage/db";
import { requestKindLabel } from "../recordingItemPresentation";

type ProjectInfoPanelProps = {
  project: RecordingProjectRecord;
  onBack: () => void;
  currentItem?: RecordingItem;
};

export function ProjectInfoPanel({ project, onBack, currentItem }: ProjectInfoPanelProps) {
  const requestCreatedAt = new Date(project.request.request.createdAt).toLocaleString();
  const importedAt = new Date(project.importedAt).toLocaleString();

  return (
    <section className="project-info-page" aria-label="Project information">
      <div className="summary-title">
        <div className="summary-title-main">
          <button type="button" className="secondary icon-button summary-back-button" onClick={onBack}>
            <span aria-hidden="true">←</span>
            <span className="visually-hidden">Back</span>
          </button>
          <div className="summary-title-text">
            <p className="eyebrow">Project info</p>
            <h2>{project.request.role.displayName}</h2>
          </div>
        </div>
      </div>
      <dl className="project-info-details">
        <div>
          <dt>Play title</dt>
          <dd>{project.request.play.title}</dd>
        </div>
        <div>
          <dt>Play ID</dt>
          <dd>{project.request.play.id}</dd>
        </div>
        <div>
          <dt>Role</dt>
          <dd>{project.request.role.displayName}</dd>
        </div>
        <div>
          <dt>Role ID</dt>
          <dd>{project.request.role.id}</dd>
        </div>
        <div>
          <dt>Request kind</dt>
          <dd>{requestKindLabel(project.request.request.kind)}</dd>
        </div>
        <div>
          <dt>Created by</dt>
          <dd>{project.request.request.createdBy}</dd>
        </div>
        <div>
          <dt>Created at</dt>
          <dd>{requestCreatedAt}</dd>
        </div>
        <div>
          <dt>Imported at</dt>
          <dd>{importedAt}</dd>
        </div>
        <div>
          <dt>Audio format</dt>
          <dd>{project.request.recording.sourceFormat.toUpperCase()}</dd>
        </div>
        <div>
          <dt>Lines</dt>
          <dd>{project.request.items.length}</dd>
        </div>
      </dl>
      {currentItem ? (
        <div>
          <p className="eyebrow">Current line</p>
          <dl className="project-info-details">
            <div>
              <dt>Segment</dt>
              <dd>{currentItem.segmentId}</dd>
            </div>
            <div>
              <dt>Output</dt>
              <dd>{currentItem.outputPath}</dd>
            </div>
            <div>
              <dt>Reason</dt>
              <dd>{currentItem.reason ?? "recording"}</dd>
            </div>
            <div>
              <dt>Line id</dt>
              <dd>{currentItem.id}</dd>
            </div>
          </dl>
        </div>
      ) : null}
      {project.request.request.notes ? <p className="notes">{project.request.request.notes}</p> : null}
    </section>
  );
}
