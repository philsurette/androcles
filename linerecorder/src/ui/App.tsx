import { useEffect, useState } from "react";
import type { RecordingItem } from "../domain/recordingItem";
import { recordingItemProgress, type RecordingItemProgress } from "../domain/recordingItemStatus";
import { importRecordingRequest, RecordingRequestImportError } from "../package/importRecordingRequest";
import { projectRepository } from "../storage/projectRepository";
import { takeRepository } from "../storage/takeRepository";
import type { RecordingProjectRecord } from "../storage/db";

export function App() {
  const [projects, setProjects] = useState<RecordingProjectRecord[]>([]);
  const [selectedProject, setSelectedProject] = useState<RecordingProjectRecord | null>(null);
  const [acceptedSegmentIds, setAcceptedSegmentIds] = useState<Set<string>>(new Set());
  const [status, setStatus] = useState("Import a Stager Recording Request to begin.");
  const [isImporting, setIsImporting] = useState(false);

  useEffect(() => {
    void loadProjects();
  }, []);

  async function loadProjects(): Promise<void> {
    setProjects(await projectRepository.list());
  }

  async function openProject(project: RecordingProjectRecord): Promise<void> {
    setSelectedProject(project);
    setStatus(`Opened ${project.request.role.displayName}.`);
    await loadAcceptedSegments(project.id);
  }

  async function loadAcceptedSegments(projectId: string): Promise<void> {
    const acceptedTakes = await takeRepository.acceptedForProject(projectId);
    setAcceptedSegmentIds(new Set(acceptedTakes.map((take) => take.segmentId)));
  }

  async function selectItem(project: RecordingProjectRecord, item: RecordingItem): Promise<void> {
    await projectRepository.setCurrentSegment(project.id, item.segmentId);
    const updatedProject = {
      ...project,
      currentSegmentId: item.segmentId
    };
    setSelectedProject(updatedProject);
    setProjects((currentProjects) =>
      currentProjects.map((candidate) => (candidate.id === updatedProject.id ? updatedProject : candidate))
    );
    setStatus(`Selected line ${item.sequence}.`);
  }

  async function importRequest(file: File): Promise<void> {
    setIsImporting(true);
    setStatus("Importing Recording Request...");
    try {
      const request = await importRecordingRequest(file);
      const project = await projectRepository.saveImportedRequest(request);
      await loadProjects();
      await openProject(project);
      setStatus(`Imported ${request.items.length} lines for ${project.request.role.displayName}.`);
    } catch (error) {
      const message =
        error instanceof RecordingRequestImportError ? error.message : "Unable to import Recording Request.";
      setStatus(message);
    } finally {
      setIsImporting(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="toolbar">
        <div>
          <p className="eyebrow">Quince</p>
          <h1>LineRecorder</h1>
        </div>
        <div className="toolbar-actions">
          {selectedProject ? (
            <button type="button" className="secondary" onClick={() => setSelectedProject(null)}>
              Library
            </button>
          ) : null}
          <ImportRequestButton isImporting={isImporting} onImport={importRequest} />
        </div>
      </section>

      <p className="status" role="status">
        {status}
      </p>

      {selectedProject ? (
        <ProjectDetail
          project={selectedProject}
          acceptedSegmentIds={acceptedSegmentIds}
          onSelectItem={(item) => void selectItem(selectedProject, item)}
        />
      ) : (
        <ProjectLibrary projects={projects} onOpenProject={(project) => void openProject(project)} />
      )}
    </main>
  );
}

type ImportRequestButtonProps = {
  isImporting: boolean;
  onImport: (file: File) => Promise<void>;
};

function ImportRequestButton({ isImporting, onImport }: ImportRequestButtonProps) {
  return (
    <label className="button">
      Import Request
      <input
        type="file"
        accept=".zip,application/zip"
        disabled={isImporting}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) {
            void onImport(file);
          }
          event.currentTarget.value = "";
        }}
      />
    </label>
  );
}

type ProjectLibraryProps = {
  projects: RecordingProjectRecord[];
  onOpenProject: (project: RecordingProjectRecord) => void;
};

function ProjectLibrary({ projects, onOpenProject }: ProjectLibraryProps) {
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
            <button type="button" onClick={() => onOpenProject(project)}>
              Open
            </button>
          </article>
        ))
      )}
    </section>
  );
}

type ProjectDetailProps = {
  project: RecordingProjectRecord;
  acceptedSegmentIds: Set<string>;
  onSelectItem: (item: RecordingItem) => void;
};

function ProjectDetail({ project, acceptedSegmentIds, onSelectItem }: ProjectDetailProps) {
  const progress = recordingItemProgress(project.request.items, acceptedSegmentIds);
  const selectedItem =
    project.currentSegmentId === undefined
      ? progress[0]
      : progress.find((candidate) => candidate.item.segmentId === project.currentSegmentId) ?? progress[0];

  return (
    <section className="project-detail" aria-label="Recording Request detail">
      <ProjectSummary project={project} progress={progress} />
      <div className="recording-workspace">
        <ItemList progress={progress} selectedSegmentId={selectedItem?.item.segmentId} onSelectItem={onSelectItem} />
        {selectedItem ? <ItemDetail progress={selectedItem} /> : null}
      </div>
    </section>
  );
}

type ProjectSummaryProps = {
  project: RecordingProjectRecord;
  progress: RecordingItemProgress[];
};

function ProjectSummary({ project, progress }: ProjectSummaryProps) {
  const acceptedCount = progress.filter((candidate) => candidate.status === "accepted").length;
  return (
    <article className="summary-panel">
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
          <dt>Progress</dt>
          <dd>
            {acceptedCount}/{progress.length}
          </dd>
        </div>
        <div>
          <dt>Format</dt>
          <dd>{project.request.recording.sourceFormat.toUpperCase()}</dd>
        </div>
      </dl>
      {project.request.request.notes ? <p className="notes">{project.request.request.notes}</p> : null}
    </article>
  );
}

type ItemListProps = {
  progress: RecordingItemProgress[];
  selectedSegmentId: string | undefined;
  onSelectItem: (item: RecordingItem) => void;
};

function ItemList({ progress, selectedSegmentId, onSelectItem }: ItemListProps) {
  return (
    <section className="item-list" aria-label="Recording items">
      {progress.map(({ item, status }) => (
        <button
          key={item.segmentId}
          type="button"
          className={item.segmentId === selectedSegmentId ? "item-row selected" : "item-row"}
          onClick={() => onSelectItem(item)}
        >
          <span className={status === "accepted" ? "status-pill accepted" : "status-pill"}>{status}</span>
          <span className="item-row-text">
            <strong>Line {item.sequence}</strong>
            <span>{item.segmentText}</span>
          </span>
        </button>
      ))}
    </section>
  );
}

type ItemDetailProps = {
  progress: RecordingItemProgress;
};

function ItemDetail({ progress }: ItemDetailProps) {
  const { item, status } = progress;
  return (
    <article className="item-detail">
      <header>
        <p className="eyebrow">{item.sectionTitle ?? "Recording Item"}</p>
        <div className="item-heading">
          <h2>Line {item.sequence}</h2>
          <span className={status === "accepted" ? "status-pill accepted" : "status-pill"}>{status}</span>
        </div>
      </header>

      <ContextBlock label="Cue" speaker={item.cueSpeaker} text={item.cueText} />
      <ContextBlock label="Previous" speaker={item.previousSpeaker} text={item.previousText} />

      <section className="line-panel" aria-label="Line to record">
        <p className="eyebrow">Your Line</p>
        <p>{item.displayText}</p>
      </section>

      {item.stageDirections.length > 0 ? (
        <section className="context-panel">
          <p className="eyebrow">Stage Directions</p>
          <ul>
            {item.stageDirections.map((direction) => (
              <li key={direction}>{direction}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <ContextBlock label="Next" speaker={item.nextSpeaker} text={item.nextText} />

      <dl className="item-metadata">
        <div>
          <dt>Segment</dt>
          <dd>{item.segmentId}</dd>
        </div>
        <div>
          <dt>Output</dt>
          <dd>{item.outputPath}</dd>
        </div>
        <div>
          <dt>Reason</dt>
          <dd>{item.reason ?? "recording"}</dd>
        </div>
      </dl>
    </article>
  );
}

type ContextBlockProps = {
  label: string;
  speaker?: string;
  text?: string;
};

function ContextBlock({ label, speaker, text }: ContextBlockProps) {
  if (!text) {
    return null;
  }
  return (
    <section className="context-panel">
      <p className="eyebrow">{label}</p>
      {speaker ? <h3>{speaker}</h3> : null}
      <p>{text}</p>
    </section>
  );
}

function requestKindLabel(kind: string): string {
  return kind
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
