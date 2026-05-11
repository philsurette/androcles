import { useEffect, useState } from "react";
import { importRecordingRequest, RecordingRequestImportError } from "../package/importRecordingRequest";
import { projectRepository } from "../storage/projectRepository";
import type { RecordingProjectRecord } from "../storage/db";

export function App() {
  const [projects, setProjects] = useState<RecordingProjectRecord[]>([]);
  const [status, setStatus] = useState("Import a Stager Recording Request to begin.");
  const [isImporting, setIsImporting] = useState(false);

  useEffect(() => {
    void loadProjects();
  }, []);

  async function loadProjects(): Promise<void> {
    setProjects(await projectRepository.list());
  }

  async function importRequest(file: File): Promise<void> {
    setIsImporting(true);
    setStatus("Importing Recording Request...");
    try {
      const request = await importRecordingRequest(file);
      const project = await projectRepository.saveImportedRequest(request);
      await loadProjects();
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
        <label className="button">
          Import Request
          <input
            type="file"
            accept=".zip,application/zip"
            disabled={isImporting}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                void importRequest(file);
              }
              event.currentTarget.value = "";
            }}
          />
        </label>
      </section>

      <p className="status" role="status">
        {status}
      </p>

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
                  <dt>Lines</dt>
                  <dd>{project.request.items.length}</dd>
                </div>
                <div>
                  <dt>Format</dt>
                  <dd>{project.request.recording.sourceFormat.toUpperCase()}</dd>
                </div>
              </dl>
            </article>
          ))
        )}
      </section>
    </main>
  );
}
