import { type ChangeEvent, useEffect, useState } from "react";
import type { Playbook } from "../../domain/playbook";
import { estimateStorage, formatBytes, requestPersistentStorage, type StorageEstimate } from "../../platform/storageEstimate";
import { installPlaybook } from "../../playbook/installPlaybook";
import { indexedDbStorage } from "../../storage/indexedDbStorage";
import { userFacingErrorMessage } from "../errors/userFacingErrorMessage";

type LibraryScreenProps = {
  onSelectPlaybook: (playbook: Playbook) => void;
};

export function LibraryScreen({ onSelectPlaybook }: LibraryScreenProps) {
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [selectedFilename, setSelectedFilename] = useState<string>("");
  const [isImporting, setIsImporting] = useState(false);
  const [importStatus, setImportStatus] = useState("");
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [storageEstimate, setStorageEstimate] = useState<StorageEstimate | null>(null);

  useEffect(() => {
    void loadPlaybooks();
    void loadStorageEstimate();
  }, []);

  async function loadPlaybooks() {
    try {
      setPlaybooks(await indexedDbStorage.playbooks.list());
    } catch (loadError) {
      setPlaybooks([]);
      setError(userFacingErrorMessage(loadError));
    }
  }

  async function loadStorageEstimate() {
    setStorageEstimate(await estimateStorage());
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
    setImportStatus("Reading Playbook...");

    try {
      const importStartedAt = performance.now();
      const playbook = await installPlaybook(file, {
        onProgress: (progress) => {
          if (progress.phase === "extracting") {
            setImportStatus("Extracting and validating Playbook...");
          } else if (progress.phase === "storing-audio") {
            setImportStatus(`Storing audio ${progress.completed} of ${progress.total}...`);
          } else {
            setImportStatus("Saving Playbook...");
          }
        }
      });
      const elapsedSeconds = (performance.now() - importStartedAt) / 1000;
      const persistence = await requestPersistentStorage();
      await loadStorageEstimate();
      await loadPlaybooks();
      setMessage(
        `Imported ${playbook.title} (${formatBytes(file.size)}) in ${elapsedSeconds.toFixed(1)}s.${
          persistence === null ? "" : persistence ? " Persistent storage is enabled." : " Persistent storage was not granted."
        }`
      );
    } catch (importError) {
      setError(userFacingErrorMessage(importError));
    } finally {
      setIsImporting(false);
      setImportStatus("");
      event.target.value = "";
    }
  }

  async function deletePlaybook(id: string) {
    try {
      await indexedDbStorage.playbooks.delete(id);
      await loadPlaybooks();
      await loadStorageEstimate();
    } catch (deleteError) {
      setError(userFacingErrorMessage(deleteError));
    }
  }

  return (
    <main className="shell">
      <section className="hero library">
        <div className="library-title-row">
          <p className="eyebrow">QUINCE CUEMASTER</p>
          <button
            type="button"
            className="secondary library-about-button"
            aria-expanded={isAboutOpen}
            aria-controls="library-about-panel"
            aria-label="About Cuemaster"
            onClick={() => setIsAboutOpen((open) => !open)}
          >
            ⓘ
          </button>
        </div>
        <div className="library-intro-row">
          <p>
            Import a playbook. Rehearse.
          </p>
        </div>
        {isAboutOpen ? (
          <section id="library-about-panel" className="library-info" role="note" aria-live="polite">
            {storageEstimate ? (
              <>
                <p>Browser storage: {formatBytes(storageEstimate.usageBytes)} used of {formatBytes(storageEstimate.quotaBytes)}.</p>
                <p>
                  {storageEstimate.persisted === null
                    ? "Storage persistence depends on browser settings."
                    : storageEstimate.persisted
                      ? "Persistent storage is enabled."
                      : "Storage is currently best effort."}
                </p>
              </>
            ) : (
              <p>Storage usage is still loading.</p>
            )}
          </section>
        ) : null}

        <div className="import-panel">
          <label className="button">
            Import Playbook
            <input type="file" accept=".zip,application/zip" onChange={handleFileSelected} />
          </label>
          {selectedFilename ? <span className="filename">{selectedFilename}</span> : null}
          {isImporting ? <span className="status">{importStatus || "Importing..."}</span> : null}
        </div>

        {message ? <p className="notice">{message}</p> : null}
        {error ? (
          <p className="error" role="alert">
            {error}
          </p>
        ) : null}

        <section className="library-list" aria-label="Imported Playbooks">
          <h2>Playbook Library</h2>
          {playbooks.length === 0 ? (
            <p className="empty">No Playbooks imported yet.</p>
          ) : (
            <ul>
              {playbooks.map((playbook) => (
                <li className="playbook-row" key={playbook.id}>
                  <div>
                    <h3>{playbook.title}</h3>
                    <p>
                      {playbook.roles.length} role{playbook.roles.length === 1 ? "" : "s"}
                    </p>
                  </div>
                  <div className="row-actions">
                    <button type="button" onClick={() => onSelectPlaybook(playbook)}>
                      Rehearse!
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
