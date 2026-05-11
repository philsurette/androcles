import { useEffect, useState } from "react";
import { importRecordingPack, RecordingPackImportError } from "../package/importRecordingPack";
import { projectRepository } from "../storage/projectRepository";
import type { RecordingProjectRecord } from "../storage/db";

export function App() {
  const [projects, setProjects] = useState<RecordingProjectRecord[]>([]);
  const [status, setStatus] = useState("Import a Stager recording pack to begin.");
  const [isImporting, setIsImporting] = useState(false);

  useEffect(() => {
    void loadProjects();
  }, []);

  async function loadProjects(): Promise<void> {
    setProjects(await projectRepository.list());
  }

  async function importPack(file: File): Promise<void> {
    setIsImporting(true);
    setStatus("Importing recording pack...");
    try {
      const pack = await importRecordingPack(file);
      const project = await projectRepository.saveImportedPack(pack);
      await loadProjects();
      setStatus(`Imported ${pack.items.length} lines for ${project.pack.role.displayName}.`);
    } catch (error) {
      const message =
        error instanceof RecordingPackImportError ? error.message : "Unable to import recording pack.";
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
          Import Pack
          <input
            type="file"
            accept=".zip,application/zip"
            disabled={isImporting}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                void importPack(file);
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
            <h2>No recording packs imported</h2>
            <p>LineRecorder stores imported packs and accepted takes locally in this browser.</p>
          </article>
        ) : (
          projects.map((project) => (
            <article key={project.id} className="project-card">
              <div>
                <p className="eyebrow">{project.pack.play.title}</p>
                <h2>{project.pack.role.displayName}</h2>
              </div>
              <dl>
                <div>
                  <dt>Lines</dt>
                  <dd>{project.pack.items.length}</dd>
                </div>
                <div>
                  <dt>Format</dt>
                  <dd>{project.pack.recording.sourceFormat.toUpperCase()}</dd>
                </div>
              </dl>
            </article>
          ))
        )}
      </section>
    </main>
  );
}
