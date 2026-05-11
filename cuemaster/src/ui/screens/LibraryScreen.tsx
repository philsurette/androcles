import { type ChangeEvent, useEffect, useState } from "react";
import type { Playbook } from "../../domain/playbook";
import { installPlaybook } from "../../playbook/installPlaybook";
import { playbookRepository } from "../../storage/playbookRepository";
import { userFacingErrorMessage } from "../errors/userFacingErrorMessage";

type LibraryScreenProps = {
  onSelectPlaybook: (playbook: Playbook) => void;
};

export function LibraryScreen({ onSelectPlaybook }: LibraryScreenProps) {
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [selectedFilename, setSelectedFilename] = useState<string>("");
  const [isImporting, setIsImporting] = useState(false);
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    void loadPlaybooks();
  }, []);

  async function loadPlaybooks() {
    try {
      setPlaybooks(await playbookRepository.list());
    } catch (loadError) {
      setPlaybooks([]);
      setError(userFacingErrorMessage(loadError));
    }
  }

  async function handleFileSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    setMessage("");
    setError("");

    if (!file) {
      setSelectedFilename("");
      return;
    }

    setSelectedFilename(file.name);
    setIsImporting(true);

    try {
      const playbook = await installPlaybook(file);
      await loadPlaybooks();
      setMessage(`Imported ${playbook.title}`);
    } catch (importError) {
      setError(userFacingErrorMessage(importError));
    } finally {
      setIsImporting(false);
      event.target.value = "";
    }
  }

  async function deletePlaybook(id: string) {
    await playbookRepository.delete(id);
    await loadPlaybooks();
  }

  return (
    <main className="shell">
      <section className="hero library">
        <p className="eyebrow">Cuemaster</p>
        <h1>Rehearse from Playbooks.</h1>
        <p>
          Import a Stager-generated Playbook, choose a role, hear your cues, and drill your
          expected responses.
        </p>

        <div className="import-panel">
          <label className="button">
            Import Playbook
            <input type="file" accept=".zip,application/zip" onChange={handleFileSelected} />
          </label>
          {selectedFilename ? <span className="filename">{selectedFilename}</span> : null}
          {isImporting ? <span className="status">Importing...</span> : null}
        </div>

        {message ? <p className="notice">{message}</p> : null}
        {error ? (
          <p className="error" role="alert">
            {error}
          </p>
        ) : null}

        <section className="library-list" aria-label="Imported Playbooks">
          <h2>Library</h2>
          {playbooks.length === 0 ? (
            <p className="empty">No Playbooks imported yet.</p>
          ) : (
            <ul>
              {playbooks.map((playbook) => (
                <li className="playbook-row" key={playbook.id}>
                  <div>
                    <h3>{playbook.title}</h3>
                    <p>
                      {playbook.roles.length} role{playbook.roles.length === 1 ? "" : "s"}:{" "}
                      {playbook.roles.map((role) => role.displayName).join(", ")}
                    </p>
                  </div>
                  <div className="row-actions">
                    <button type="button" onClick={() => onSelectPlaybook(playbook)}>
                      Open
                    </button>
                    <button type="button" className="secondary" onClick={() => void deletePlaybook(playbook.id)}>
                      Remove
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </section>
    </main>
  );
}
