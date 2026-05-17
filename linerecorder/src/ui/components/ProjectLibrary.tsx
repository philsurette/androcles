import type { RecordingProjectRecord } from "../../storage/db";
import { requestKindLabel } from "../recordingItemPresentation";

type ProjectLibraryProps = {
  projects: RecordingProjectRecord[];
  onOpenProject: (project: RecordingProjectRecord) => void;
  onDeleteProject: (project: RecordingProjectRecord) => void;
};

export function ProjectLibrary({ projects, onOpenProject, onDeleteProject }: ProjectLibraryProps) {
  return (
    <section className="project-list" aria-label="Recording projects">
      {projects.length === 0 ? (
        <article className="empty-state">
          <h2>No Recording Requests imported</h2>
          <p>LineRecorder stores imported requests and accepted takes locally in this browser.</p>
        </article>
      ) : (
        projects.map((project) => (
          <article key={project.id} className="project-card">
            <div>
              <p className="eyebrow">{project.request.play.title}</p>
              <h2>{project.request.role.displayName}</h2>
            </div>
            <dl>
              <div>
                <dt>Request</dt>
                <dd>{requestKindLabel(project.request.request.kind)}</dd>
              </div>
              <div>
                <dt>Lines</dt>
                <dd>{project.request.items.length}</dd>
              </div>
            </dl>
            <div className="project-card-actions">
              <button type="button" onClick={() => onOpenProject(project)}>
                Open
              </button>
              <button type="button" className="secondary danger summary-action-icon" onClick={() => onDeleteProject(project)}>
                <span aria-hidden="true">🗑</span>
                <span className="visually-hidden">Delete project</span>
              </button>
            </div>
          </article>
        ))
      )}
    </section>
  );
}
