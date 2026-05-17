import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { MicrophoneSession, type MicrophoneReading } from "../audio/microphoneSession";
import { meterFillPercentForLevel } from "../audio/inputMeter";
import { WavRecorder, type RecordedWav, type WavRecorderReading } from "../audio/wavRecorder";
import type { FloorNoiseRecording } from "../domain/floorNoiseRecording";
import type { RecordingItem } from "../domain/recordingItem";
import { recordingItemProgress, type RecordingItemProgress } from "../domain/recordingItemStatus";
import { nextProgress, previousProgress, selectedProgressIndex } from "../domain/recordingNavigation";
import type { RecordingTake } from "../domain/take";
import { exportRoleRecordings, RoleRecordingsExportError } from "../package/exportRoleRecordings";
import { importRecordingRequest, RecordingRequestImportError } from "../package/importRecordingRequest";
import { browserDownloadService } from "../platform/download";
import { listMicrophoneDevices, MicrophonePermissionError, type MicrophoneDevice, type MicrophoneMode } from "../platform/microphone";
import { projectRepository } from "../storage/projectRepository";
import { floorNoiseRepository } from "../storage/floorNoiseRepository";
import { takeRepository } from "../storage/takeRepository";
import type { RecordingProjectRecord } from "../storage/db";

export function App() {
  const [projects, setProjects] = useState<RecordingProjectRecord[]>([]);
  const [selectedProject, setSelectedProject] = useState<RecordingProjectRecord | null>(null);
  const [isProjectInfoMode, setIsProjectInfoMode] = useState(false);
  const [acceptedItemIds, setAcceptedItemIds] = useState<Set<string>>(new Set());
  const [status, setStatus] = useState("Import a Stager Recording Request to begin.");
  const [isImporting, setIsImporting] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    void loadProjects();
  }, []);

  async function loadProjects(): Promise<void> {
    setProjects(await projectRepository.list());
  }

  async function openProject(project: RecordingProjectRecord): Promise<void> {
    setSelectedProject(project);
    setIsProjectInfoMode(false);
    setStatus(`Opened ${project.request.role.displayName}.`);
    await loadAcceptedSegments(project.id);
  }

  async function loadAcceptedSegments(projectId: string): Promise<void> {
    const acceptedTakes = await takeRepository.acceptedForProject(projectId);
    setAcceptedItemIds(new Set(acceptedTakes.map((take) => take.segmentId)));
  }

  async function selectItem(project: RecordingProjectRecord, item: RecordingItem): Promise<void> {
    await projectRepository.setCurrentItem(project.id, item.id);
    const updatedProject = {
      ...project,
      currentItemId: item.id
    };
    setSelectedProject(updatedProject);
    setProjects((currentProjects) =>
      currentProjects.map((candidate) => (candidate.id === updatedProject.id ? updatedProject : candidate))
    );
    setStatus(`Selected ${item.id}.`);
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

  async function exportProject(project: RecordingProjectRecord): Promise<void> {
    setIsExporting(true);
    setStatus("Exporting role recordings...");
    try {
      const acceptedTakes = await takeRepository.acceptedForProject(project.id);
      const floorNoiseRecordings = await floorNoiseRepository.forProject(project.id);
      const exported = await exportRoleRecordings(project, acceptedTakes, floorNoiseRecordings);
      browserDownloadService.download({ blob: exported.blob, fileName: exported.fileName });
      const exportedCount = exported.manifest.recordings.length;
      const missingCount = exported.manifest.missing_segment_ids.length;
      setStatus(
        exported.manifest.complete
          ? `Exported ${exported.fileName} with ${exportedCount} recordings. Send this zip to the showrunner.`
          : `Exported partial package ${exported.fileName} with ${exportedCount} recordings; ${missingCount} still missing. Send this zip to the showrunner.`
      );
    } catch (error) {
      setStatus(error instanceof RoleRecordingsExportError ? error.message : "Unable to export role recordings.");
    } finally {
      setIsExporting(false);
    }
  }

  async function deleteProject(project: RecordingProjectRecord): Promise<void> {
    const confirmed = window.confirm(
      `Delete ${project.request.role.displayName} for ${project.request.play.title}? This removes the local request and all saved takes from this browser.`
    );
    if (!confirmed) {
      return;
    }

    await projectRepository.delete(project.id);
    if (selectedProject?.id === project.id) {
      setSelectedProject(null);
      setIsProjectInfoMode(false);
    }
    await loadProjects();
    setStatus(`Deleted local recordings for ${project.request.role.displayName}.`);
  }

  return (
    <main className="app-shell">
      {selectedProject ? (
        isProjectInfoMode ? (
          <ProjectInfoPanel
            project={selectedProject}
            onBack={() => setIsProjectInfoMode(false)}
            currentItem={selectedProject.request.items.find((item) => item.id === selectedProject.currentItemId)}
          />
        ) : (
          <ProjectDetail
            project={selectedProject}
            acceptedItemIds={acceptedItemIds}
            status={status}
            onSelectItem={(item) => void selectItem(selectedProject, item)}
            onAccepted={() => loadAcceptedSegments(selectedProject.id)}
            onExport={() => void exportProject(selectedProject)}
            onBack={() => setSelectedProject(null)}
            onViewInfo={(item) => {
              setSelectedProject((current) =>
                current === null ? current : { ...current, currentItemId: item?.id ?? current.currentItemId }
              );
              setIsProjectInfoMode(true);
            }}
            isExporting={isExporting}
          />
        )
      ) : (
        <>
          <section className="toolbar">
            <div>
              <p className="eyebrow">Quince</p>
              <h1>LineRecorder</h1>
            </div>
            <div className="toolbar-actions">
              <ImportRequestButton isImporting={isImporting} onImport={importRequest} />
            </div>
          </section>

          <p className="status" role="status">
            {status}
          </p>

          <ProjectLibrary
            projects={projects}
            onOpenProject={(project) => void openProject(project)}
            onDeleteProject={(project) => void deleteProject(project)}
          />
        </>
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
  onDeleteProject: (project: RecordingProjectRecord) => void;
};

function ProjectLibrary({ projects, onOpenProject, onDeleteProject }: ProjectLibraryProps) {
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

type ProjectDetailProps = {
  project: RecordingProjectRecord;
  acceptedItemIds: Set<string>;
  status: string;
  onSelectItem: (item: RecordingItem) => void;
  onAccepted: () => Promise<void>;
  onExport: () => void;
  onViewInfo: (item?: RecordingItem) => void;
  onBack: () => void;
  isExporting: boolean;
};

function ProjectDetail({
  project,
  acceptedItemIds,
  status,
  onSelectItem,
  onAccepted,
  onExport,
  onBack,
  onViewInfo,
  isExporting
}: ProjectDetailProps) {
  const [microphoneConfig, setMicrophoneConfig] = useState<MicrophoneConfig | null>(null);
  const [microphoneReading, setMicrophoneReading] = useState<MicrophoneReading>({ energy: 0, level: "no-signal" });
  const [isExplorerOpen, setIsExplorerOpen] = useState(false);
  const [isMicrophoneSetupOpen, setIsMicrophoneSetupOpen] = useState(false);
  const progress = recordingItemProgress(project.request.items, acceptedItemIds);
  const selectedIndex = selectedProgressIndex(progress, project.currentItemId);
  const selectedItem = selectedIndex === -1 ? undefined : progress[selectedIndex];
  const previousItem = previousProgress(progress, selectedIndex);
  const nextItem = nextProgress(progress, selectedIndex);

  if (isMicrophoneSetupOpen) {
    return (
      <section className="project-detail microphone-config-page" aria-label="Microphone setup">
        <div className="summary-title">
          <div className="summary-title-main">
            <button type="button" className="secondary icon-button summary-back-button" onClick={() => setIsMicrophoneSetupOpen(false)}>
              <span aria-hidden="true">←</span>
              <span className="visually-hidden">Back</span>
            </button>
            <div className="summary-title-text">
              <p className="eyebrow">Microphone</p>
              <h2>Microphone setup</h2>
            </div>
          </div>
        </div>
        <MicrophoneSetup
          project={project}
          onReady={setMicrophoneConfig}
          onReading={setMicrophoneReading}
          onDone={() => setIsMicrophoneSetupOpen(false)}
        />
      </section>
    );
  }

  return (
    <section className="project-detail recording-page" aria-label="Recording Request detail">
      <ProjectSummary
        project={project}
        progress={progress}
        onExport={onExport}
        onViewInfo={onViewInfo}
        onBack={onBack}
        isExplorerOpen={isExplorerOpen}
        onToggleExplorer={() => setIsExplorerOpen((current) => !current)}
        isExporting={isExporting}
      />
      <MicrophoneStrip config={microphoneConfig} reading={microphoneReading} onOpen={() => setIsMicrophoneSetupOpen(true)} />
      <div className={isExplorerOpen ? "recording-workspace" : "recording-workspace explorer-collapsed"}>
        <ItemList
          progress={progress}
          selectedItemId={selectedItem?.item.id}
          isOpen={isExplorerOpen}
          onToggleOpen={() => setIsExplorerOpen((current) => !current)}
          onSelectItem={onSelectItem}
        />
        {selectedItem ? (
          <ItemDetail
            project={project}
            progress={selectedItem}
            itemNumber={selectedIndex + 1}
            itemCount={progress.length}
            microphoneConfig={microphoneConfig}
            previousItem={previousItem}
            nextItem={nextItem}
            onNavigate={onSelectItem}
            onAccepted={onAccepted}
          />
        ) : null}
      </div>
    </section>
  );
}

type MicrophoneConfig = {
  deviceId: string;
  deviceLabel: string;
  mode: MicrophoneMode;
};

type MicrophoneSetupProps = {
  project: RecordingProjectRecord;
  onReady: (config: MicrophoneConfig | null) => void;
  onReading: (reading: MicrophoneReading) => void;
  onDone: () => void;
};

function MicrophoneSetup({ project, onReady, onReading, onDone }: MicrophoneSetupProps) {
  const sessionRef = useRef<MicrophoneSession | null>(null);
  const floorNoiseRecorderRef = useRef<WavRecorder | null>(null);
  const [devices, setDevices] = useState<MicrophoneDevice[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [mode, setMode] = useState<MicrophoneMode>("clean");
  const [reading, setReading] = useState<MicrophoneReading>({ energy: 0, level: "no-signal" });
  const [status, setStatus] = useState("Microphone not started.");
  const [isActive, setIsActive] = useState(false);
  const [isCapturingFloorNoise, setIsCapturingFloorNoise] = useState(false);

  useEffect(() => {
    onReading(reading);
  }, [reading, onReading]);

  useEffect(() => {
    return () => {
      sessionRef.current?.stop();
      floorNoiseRecorderRef.current?.stopWithoutResult();
    };
  }, []);

  async function refreshDevices(): Promise<void> {
    const availableDevices = await listMicrophoneDevices();
    setDevices(availableDevices);
    if (!selectedDeviceId && availableDevices[0]) {
      setSelectedDeviceId(availableDevices[0].deviceId);
    }
  }

  async function startMicrophone(): Promise<void> {
    try {
      setStatus("Requesting microphone permission...");
      await refreshDevices();
      const session = new MicrophoneSession((nextReading) => {
        setReading(nextReading);
        setStatus(levelStatus(nextReading.level));
      });
      sessionRef.current = session;
      await session.start(selectedDeviceId, mode);
      onReady({ deviceId: selectedDeviceId, deviceLabel: selectedDeviceLabel(), mode });
      setIsActive(true);
    } catch (error) {
      const message =
        error instanceof MicrophonePermissionError ? error.message : "Unable to start microphone setup.";
      setStatus(message);
      setIsActive(false);
    }
  }

  function stopMicrophone(): void {
    floorNoiseRecorderRef.current?.stopWithoutResult();
    floorNoiseRecorderRef.current = null;
    sessionRef.current?.stop();
    sessionRef.current = null;
    onReady(null);
    setIsActive(false);
    setIsCapturingFloorNoise(false);
    setReading({ energy: 0, level: "no-signal" });
    setStatus("Microphone stopped.");
    onReading({ energy: 0, level: "no-signal" });
  }

  async function captureFloorNoise(): Promise<void> {
    if (!isActive) {
      return;
    }
    try {
      setIsCapturingFloorNoise(true);
      setStatus("Stay silent...");
      const recorder = new WavRecorder();
      floorNoiseRecorderRef.current = recorder;
      await recorder.start(selectedDeviceId, mode);
      await sleep(5000);
      const recorded = recorder.stop();
      floorNoiseRecorderRef.current = null;
      if (!isUsableFloorNoise(recorded)) {
        setStatus("Room tone was too loud. Try again while silent.");
        return;
      }
      const recordedAt = new Date().toISOString();
      const floorNoise: FloorNoiseRecording = {
        id: `floor-${recordedAt.replace(/[-:.]/g, "").replace("Z", "Z")}`,
        projectId: project.id,
        recordedAt,
        durationMs: recorded.durationMs,
        sampleRateHz: recorded.sampleRateHz,
        channels: recorded.channels,
        deviceId: selectedDeviceId,
        deviceLabel: selectedDeviceLabel(),
        mode,
        inputQuality: recordingInputQuality(recorded),
        blob: recorded.blob
      };
      await floorNoiseRepository.save(floorNoise);
      setStatus(`Room tone captured ${new Date(recordedAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}.`);
    } catch {
      floorNoiseRecorderRef.current?.stopWithoutResult();
      floorNoiseRecorderRef.current = null;
      setStatus("Unable to capture room tone.");
    } finally {
      setIsCapturingFloorNoise(false);
    }
  }

  function selectedDeviceLabel(): string {
    return devices.find((device) => device.deviceId === selectedDeviceId)?.label || "Default microphone";
  }

  const showStatus =
    status === "Requesting microphone permission..." ||
    status === "Unable to start microphone setup." ||
    status === "Stay silent..." ||
    status.startsWith("Room tone") ||
    status === "Unable to capture room tone." ||
    status.startsWith("Microphone access");

  return (
    <section className="microphone-panel compact" aria-label="Microphone setup">
      <div className="microphone-heading">
        <span className={isActive ? "microphone-glyph active" : "microphone-glyph"} aria-label={isActive ? "Microphone ready" : "Microphone setup"}>
          🎙
        </span>
        <div className="microphone-actions">
          <button type="button" className="secondary" onClick={onDone}>
            OK
          </button>
        </div>
      </div>
      <div className="microphone-controls">
        <label>
          <span className="visually-hidden">Input</span>
          <select
            value={selectedDeviceId}
            disabled={isActive && isCapturingFloorNoise}
            onFocus={() => void refreshDevices()}
            onChange={(event) => setSelectedDeviceId(event.target.value)}
          >
            {devices.length === 0 ? <option value="">Default microphone</option> : null}
            {devices.map((device) => (
              <option key={device.deviceId} value={device.deviceId}>
                {device.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="visually-hidden">Mode</span>
          <select
            value={mode}
            disabled={isActive && isCapturingFloorNoise}
            onChange={(event) => setMode(event.target.value as MicrophoneMode)}
          >
            <option value="clean">Clean room</option>
            <option value="noisy">Noisy room</option>
          </select>
        </label>
        {isActive ? (
          <button type="button" className="secondary" onClick={stopMicrophone} disabled={isCapturingFloorNoise}>
            Stop Mic
          </button>
        ) : (
          <button type="button" onClick={() => void startMicrophone()}>
            Start Mic
          </button>
        )}
        <button
          type="button"
          className="secondary"
          disabled={!isActive || isCapturingFloorNoise}
          onClick={() => void captureFloorNoise()}
        >
          {isCapturingFloorNoise ? "Capturing..." : "Room Tone"}
        </button>
      </div>
      <div className="meter-row">
        <div className="meter" aria-label={`Input level: ${levelLabel(reading.level)}`}>
          <span style={{ width: `${meterFillPercentForLevel(reading.energy, reading.level)}%` }} />
        </div>
        <span className={`meter-label ${reading.level}`}>{levelLabel(reading.level)}</span>
      </div>
      {showStatus ? <p className="microphone-status">{status}</p> : null}
    </section>
  );
}

type MicrophoneStripProps = {
  config: MicrophoneConfig | null;
  reading: MicrophoneReading;
  onOpen: () => void;
};

function MicrophoneStrip({ config, reading, onOpen }: MicrophoneStripProps) {
  const label = config ? "Mic Open" : "Start Mic";

  return (
    <section className="microphone-strip" aria-label="Microphone">
      <span className={config ? "microphone-glyph active" : "microphone-glyph"} aria-label="Microphone">
        🎙
      </span>
      <div className="meter-row">
        <div className="meter" aria-label={`Input level: ${levelLabel(reading.level)}`}>
          <span style={{ width: `${meterFillPercentForLevel(reading.energy, reading.level)}%` }} />
        </div>
        <span className={`meter-label ${reading.level}`}>{levelLabel(reading.level)}</span>
      </div>
      <button type="button" className={config ? "secondary" : "button"} onClick={onOpen}>
        {label}
      </button>
    </section>
  );
}

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

function ProjectSummary({
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

type ProjectInfoPanelProps = {
  project: RecordingProjectRecord;
  onBack: () => void;
  currentItem?: RecordingItem;
};

function ProjectInfoPanel({ project, onBack, currentItem }: ProjectInfoPanelProps) {
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

type ItemListProps = {
  progress: RecordingItemProgress[];
  selectedItemId: string | undefined;
  isOpen: boolean;
  onToggleOpen: () => void;
  onSelectItem: (item: RecordingItem) => void;
};

function ItemList({ progress, selectedItemId, isOpen, onToggleOpen, onSelectItem }: ItemListProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const acceptedCount = progress.filter((candidate) => candidate.status === "accepted").length;
  const selectedRowRef = useRef<HTMLButtonElement | null>(null);
  const normalizedSearchQuery = searchQuery.trim().toLocaleLowerCase();
  const filteredProgress = progress.filter(({ item }) =>
    recordingItemSearchText(item).toLocaleLowerCase().includes(normalizedSearchQuery)
  );

  useLayoutEffect(() => {
    if (isOpen) {
      selectedRowRef.current?.scrollIntoView({ block: "nearest" });
    }
  }, [isOpen, selectedItemId]);

  if (!isOpen) {
    return null;
  }

  return (
    <aside className="item-explorer" aria-label="Recording items">
      <div className="item-explorer-header">
        <div>
          <p className="eyebrow">Lines</p>
          <strong>{acceptedCount}/{progress.length} requested recordings completed</strong>
        </div>
        <button type="button" className="explorer-disclosure-button expanded" aria-label="Hide line list" title="Hide line list" onClick={onToggleOpen}>
          <span className="context-disclosure" aria-hidden="true" />
        </button>
      </div>
      <label className="item-search">
        <span>Search lines</span>
        <div>
          <input
            type="search"
            value={searchQuery}
            placeholder="Find a cue or line"
            onChange={(event) => setSearchQuery(event.target.value)}
          />
          {searchQuery ? (
            <button type="button" aria-label="Clear line search." onClick={() => setSearchQuery("")}>
              ×
            </button>
          ) : null}
        </div>
      </label>
      <div className="item-list">
        {filteredProgress.length === 0 ? <p className="item-empty">No matching lines.</p> : null}
        {filteredProgress.map(({ item, status }) => (
          <button
            key={item.id}
            ref={item.id === selectedItemId ? selectedRowRef : undefined}
            type="button"
            className={item.id === selectedItemId ? "item-row selected" : "item-row"}
            onClick={() => onSelectItem(item)}
          >
            <span className={status === "accepted" ? "status-dot accepted" : "status-dot"} aria-label={status} title={status} />
            <strong>{item.id}</strong>
            <span>{item.segmentText}</span>
          </button>
        ))}
      </div>
    </aside>
  );
}

export function recordingItemSearchText(item: RecordingItem): string {
  return [
    item.id,
    item.lineId,
    item.displayText,
    item.segmentText,
    item.cueSpeaker,
    item.cueText,
    item.previousSpeaker,
    item.previousText,
    item.nextSpeaker,
    item.nextText,
    item.sectionTitle,
    item.sceneHeading,
    item.reason,
    item.notes,
    ...item.stageDirections,
    ...item.blocking.map((blocking) => `${blocking.targets.join(" ")} ${blocking.text}`)
  ]
    .filter(Boolean)
    .join(" ");
}

type ItemDetailProps = {
  project: RecordingProjectRecord;
  progress: RecordingItemProgress;
  itemNumber: number;
  itemCount: number;
  microphoneConfig: MicrophoneConfig | null;
  previousItem: RecordingItemProgress | undefined;
  nextItem: RecordingItemProgress | undefined;
  onNavigate: (item: RecordingItem) => void;
  onAccepted: () => Promise<void>;
};

function ItemDetail({
  project,
  progress,
  itemNumber,
  itemCount,
  microphoneConfig,
  previousItem,
  nextItem,
  onNavigate,
  onAccepted
}: ItemDetailProps) {
  const { item, status } = progress;
  const showPrevious = !sameContext(item.previousSpeaker, item.previousText, item.cueSpeaker, item.cueText);
  return (
    <article className="item-detail">
      <header className="item-detail-header">
        <div className="item-heading">
          <h2>{item.id}</h2>
          <span className="line-position">line {itemNumber} of {itemCount}</span>
          <span className={status === "accepted" ? "status-pill accepted" : "status-pill"}>{status}</span>
          <span className="reason-pill">{reasonLabel(item.reason)}</span>
          <span className="line-navigation-spacer" />
          <button
            type="button"
            className="secondary icon-button"
            disabled={!previousItem}
            aria-label="Previous unaccepted line"
            title="Previous unaccepted line"
            onClick={() => previousItem && onNavigate(previousItem.item)}
          >
            &larr;
          </button>
          <button
            type="button"
            className="secondary icon-button"
            disabled={!nextItem}
            aria-label="Next unaccepted line"
            title="Next unaccepted line"
            onClick={() => nextItem && onNavigate(nextItem.item)}
          >
            &rarr;
          </button>
        </div>
      </header>

      <ContextBlock label="Cue" speaker={item.cueSpeaker} text={item.cueText} labelPosition="border" />
      {showPrevious ? <ContextBlock label="Previous" speaker={item.previousSpeaker} text={item.previousText} /> : null}

      <section className="line-panel" aria-label="Line to record">
        <div className="line-control-strip">
          <TakeRecorder
            project={project}
            item={item}
            microphoneConfig={microphoneConfig}
            onAccepted={onAccepted}
            onNavigatePrevious={previousItem ? () => onNavigate(previousItem.item) : undefined}
            onNavigateNext={nextItem ? () => onNavigate(nextItem.item) : undefined}
          />
        </div>
        <p className="line-text">{item.displayText}</p>
      </section>

      {item.stageDirections.length > 0 ? (
        <section className="stage-directions-panel">
          <p className="eyebrow">Stage Directions</p>
          <ul>
            {item.stageDirections.map((direction) => (
              <li key={direction}>{direction}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {item.blocking.length > 0 ? (
        <section className="stage-directions-panel">
          <p className="eyebrow">Blocking</p>
          <ul>
            {item.blocking.map((blocking) => (
              <li key={blocking.id}>
                <strong>{blocking.targets.join(", ")}</strong>: {blocking.text}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <ContextBlock label="Next" speaker={item.nextSpeaker} text={item.nextText} labelPosition="border" />

    </article>
  );
}

type TakeRecorderProps = {
  project: RecordingProjectRecord;
  item: RecordingItem;
  microphoneConfig: MicrophoneConfig | null;
  onAccepted: () => Promise<void>;
  onNavigatePrevious?: () => void;
  onNavigateNext?: () => void;
};

function TakeRecorder({
  project,
  item,
  microphoneConfig,
  onAccepted,
  onNavigatePrevious,
  onNavigateNext
}: TakeRecorderProps) {
  const recorderRef = useRef<WavRecorder | null>(null);
  const playbackUrlRef = useRef<string | null>(null);
  const playbackAudioRef = useRef<HTMLAudioElement | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [currentTake, setCurrentTake] = useState<RecordedWav | null>(null);
  const [acceptedTake, setAcceptedTake] = useState<RecordingTake | null>(null);
  const [recordingReading, setRecordingReading] = useState<WavRecorderReading>({ energy: 0, level: "no-signal" });
  const [playingSource, setPlayingSource] = useState<"take" | "saved" | null>(null);
  const [status, setStatus] = useState("Checking saved take...");
  const [statusTone, setStatusTone] = useState<"normal" | "warning">("normal");

  useEffect(() => {
    return () => {
      recorderRef.current?.stopWithoutResult();
      stopPlayback();
    };
  }, []);

  useEffect(() => {
    recorderRef.current?.stopWithoutResult();
    setIsRecording(false);
    setCurrentTake(null);
    setAcceptedTake(null);
    setRecordingReading({ energy: 0, level: "no-signal" });
    setStatus("Checking saved take...");
    setStatusTone("normal");
    stopPlayback();
    void loadAcceptedTake();
  }, [item.id]);

  useEffect(() => {
    if (microphoneConfig && statusTone === "warning" && status === "Start microphone setup before recording.") {
      setStatus(currentTake ? "Ready to accept or discard take." : acceptedTake ? `Accepted take saved: ${Math.round(acceptedTake.durationMs)} ms.` : "Ready to record.");
      setStatusTone("normal");
    }
  }, [microphoneConfig, status, statusTone, currentTake, acceptedTake]);

  async function loadAcceptedTake(): Promise<void> {
    const take = await takeRepository.acceptedForSegment(project.id, item.id);
    setAcceptedTake(take ?? null);
    setStatus(take ? `Accepted take saved: ${Math.round(take.durationMs)} ms.` : "No take recorded.");
    setStatusTone("normal");
  }

  async function startRecording(): Promise<void> {
    if (!microphoneConfig) {
      setStatus("Start microphone setup before recording.");
      setStatusTone("warning");
      return;
    }
    try {
      stopPlayback();
      const recorder = new WavRecorder(setRecordingReading);
      recorderRef.current = recorder;
      setCurrentTake(null);
      setRecordingReading({ energy: 0, level: "no-signal" });
      setStatus("Recording...");
      setStatusTone("normal");
      await recorder.start(microphoneConfig.deviceId, microphoneConfig.mode);
      setIsRecording(true);
    } catch {
      setStatus("Unable to start recording.");
      setStatusTone("warning");
      setIsRecording(false);
    }
  }

  function stopRecording(): void {
    if (!recorderRef.current) {
      return;
    }
    const take = recorderRef.current.stop();
    recorderRef.current = null;
    setCurrentTake(take);
    setIsRecording(false);
    setRecordingReading({ energy: 0, level: "no-signal" });
    setStatus(`Recorded ${Math.round(take.durationMs)} ms.`);
    setStatusTone("normal");
  }

  function playTake(): void {
    if (!currentTake) {
      return;
    }
    playBlob(currentTake.blob, "take");
  }

  function playAcceptedTake(): void {
    if (!acceptedTake) {
      return;
    }
    playBlob(acceptedTake.blob, "saved");
  }

  async function acceptTake(): Promise<void> {
    if (!currentTake) {
      return;
    }
    const take: RecordingTake = {
      id: `${project.id}:${item.id}:${new Date().toISOString()}`,
      projectId: project.id,
      segmentId: item.id,
      status: "accepted",
      recordedAt: new Date().toISOString(),
      durationMs: currentTake.durationMs,
      sampleRateHz: currentTake.sampleRateHz,
      channels: currentTake.channels,
      inputQuality: {
        peakEnergy: currentTake.inputQuality.peakEnergy,
        levelCounts: {
          noSignal: currentTake.inputQuality.levelCounts["no-signal"],
          tooQuiet: currentTake.inputQuality.levelCounts["too-quiet"],
          good: currentTake.inputQuality.levelCounts.good,
          clipping: currentTake.inputQuality.levelCounts.clipping
        }
      },
      blob: currentTake.blob
    };
    await takeRepository.saveAccepted(take);
    setAcceptedTake(take);
    setCurrentTake(null);
    setStatus("Take accepted.");
    setStatusTone("normal");
    await onAccepted();
  }

  function discardTake(): void {
    setCurrentTake(null);
    setRecordingReading({ energy: 0, level: "no-signal" });
    setStatus(acceptedTake ? `Accepted take saved: ${Math.round(acceptedTake.durationMs)} ms.` : "No take recorded.");
    setStatusTone("normal");
    stopPlayback();
  }

  function stopPlayback(): void {
    if (playbackAudioRef.current) {
      playbackAudioRef.current.pause();
      playbackAudioRef.current.currentTime = 0;
      playbackAudioRef.current = null;
    }
    if (playbackUrlRef.current) {
      URL.revokeObjectURL(playbackUrlRef.current);
      playbackUrlRef.current = null;
    }
    setPlayingSource(null);
  }

  function playBlob(blob: Blob, source: "take" | "saved"): void {
    stopPlayback();
    const url = URL.createObjectURL(blob);
    playbackUrlRef.current = url;
    const audio = new Audio(url);
    playbackAudioRef.current = audio;
    setPlayingSource(source);
    audio.onended = stopPlayback;
    audio.onerror = stopPlayback;
    void audio.play();
  }

  return (
    <section className="take-panel" aria-label="Take recorder">
      {isRecording ? (
        <div className="take-controls recording-active">
          <button type="button" className="record-control stop-control" aria-label="Stop recording" title="Stop recording" onClick={stopRecording}>
            <span aria-hidden="true">■</span>
          </button>
          <div className="meter-row take-meter">
            <div className="meter" aria-label={`Recording input level: ${levelLabel(recordingReading.level)}`}>
              <span style={{ width: `${meterFillPercentForLevel(recordingReading.energy, recordingReading.level)}%` }} />
            </div>
            <span className={`meter-label ${recordingReading.level}`}>{levelLabel(recordingReading.level)}</span>
          </div>
        </div>
      ) : (
        <div className="take-controls">
          <div className="take-control-group">
            <button
              type="button"
              className="record-control"
              aria-label={currentTake ? "Record another take" : acceptedTake ? "Record replacement take" : "Record"}
              title={currentTake ? "Record another take" : acceptedTake ? "Record replacement take" : "Record"}
              onClick={() => void startRecording()}
            >
              <span aria-hidden="true">●</span>
            </button>
            {playingSource === "take" || playingSource === "saved" ? (
              <button type="button" className="secondary recorder-icon-button" aria-label="Stop playback" title="Stop playback" onClick={stopPlayback}>
                <span aria-hidden="true">■</span>
              </button>
            ) : (
              <button
                type="button"
                className="secondary recorder-icon-button"
                disabled={!currentTake && !acceptedTake}
                aria-label="Play take"
                title="Play take"
                onClick={() => (currentTake ? playTake() : playAcceptedTake())}
              >
                <span aria-hidden="true">▶</span>
              </button>
            )}
            <button
              type="button"
              className="secondary recorder-icon-button accept-control"
              disabled={!currentTake || isRecording}
              aria-label="Accept take"
              title="Accept take"
              onClick={() => void acceptTake()}
            >
              <span aria-hidden="true">✓</span>
            </button>
            {currentTake ? (
              <button
                type="button"
                className="secondary recorder-icon-button discard-control"
                disabled={isRecording}
                aria-label="Discard current take"
                title="Discard current take"
                onClick={discardTake}
              >
                <span aria-hidden="true">×</span>
              </button>
            ) : null}
          </div>
          <div className="take-control-group">
            <button
              type="button"
              className="secondary recorder-icon-button"
              disabled={!onNavigatePrevious}
              aria-label="Previous unaccepted line"
              title="Previous unaccepted line"
              onClick={() => onNavigatePrevious?.()}
            >
              <span aria-hidden="true">◁</span>
            </button>
            <button
              type="button"
              className="secondary recorder-icon-button"
              disabled={!onNavigateNext}
              aria-label="Next unaccepted line"
              title="Next unaccepted line"
              onClick={() => onNavigateNext?.()}
            >
              <span aria-hidden="true">▷</span>
            </button>
          </div>
        </div>
      )}
      <div className="take-status-row">
        <p className={statusTone === "warning" ? "take-status warning" : "take-status"}>{status}</p>
      </div>
    </section>
  );
}

type ContextBlockProps = {
  label: string;
  speaker?: string;
  text?: string;
  labelPosition?: "inline" | "border";
};

function ContextBlock({ label, speaker, text, labelPosition = "inline" }: ContextBlockProps) {
  const textRef = useRef<HTMLParagraphElement | null>(null);
  const [isOverflowing, setIsOverflowing] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const cropFromStart = label !== "Next";

  useLayoutEffect(() => {
    function positionText() {
      const textElement = textRef.current;
      if (!textElement) {
        return;
      }
      setIsOverflowing(textElement.scrollWidth > textElement.clientWidth);
      textElement.scrollLeft = cropFromStart ? textElement.scrollWidth - textElement.clientWidth : 0;
    }

    positionText();
    const resizeObserver = new ResizeObserver(positionText);
    if (textRef.current) {
      resizeObserver.observe(textRef.current);
    }
    return () => resizeObserver.disconnect();
  }, [text, isOverflowing, cropFromStart]);

  if (!text) {
    return null;
  }
  const contentId = `context-${label.toLowerCase().replace(/\s+/g, "-")}-${speaker ?? "text"}`;
  const isBorderLabel = labelPosition === "border";

  return (
    <section className={isExpanded ? `context-panel expanded ${isBorderLabel ? "context-panel--border-label" : ""}`.trim() : `context-panel${isBorderLabel ? " context-panel--border-label" : ""}`}>
      {isBorderLabel ? <span className="context-border-label">{label}</span> : null}
      <button
        type="button"
        className="context-toggle"
        aria-expanded={isExpanded}
        aria-controls={contentId}
        title={isExpanded ? `Collapse ${label.toLowerCase()}` : `Expand ${label.toLowerCase()}`}
        onClick={() => setIsExpanded((current) => !current)}
      >
        <span className={isBorderLabel ? "visually-hidden" : "context-label"}>{label}</span>
        {speaker ? <span className="context-speaker">{speaker}</span> : null}
        <span className={cropFromStart ? "context-text-window" : "context-text-window crop-end"}>
          {isOverflowing && !isExpanded && cropFromStart ? (
            <span className="context-overflow-prefix" aria-hidden="true">…</span>
          ) : null}
          <p className="context-text-clip" id={contentId} ref={textRef}>
            {text}
          </p>
        </span>
        <span className="context-disclosure" aria-hidden="true" />
      </button>
      {isExpanded ? (
        <p className="context-expanded-text" aria-hidden="true">
          {text}
        </p>
      ) : null}
    </section>
  );
}

function requestKindLabel(kind: string): string {
  return kind
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function reasonLabel(reason: string | undefined): string {
  return (reason ?? "recording").replace(/_/g, " ");
}

function levelLabel(level: MicrophoneReading["level"]): string {
  switch (level) {
    case "no-signal":
      return "No signal";
    case "too-quiet":
      return "Too quiet";
    case "good":
      return "Good";
    case "clipping":
      return "Clipping";
  }
}

function levelStatus(level: MicrophoneReading["level"]): string {
  switch (level) {
    case "no-signal":
      return "No microphone signal detected.";
    case "too-quiet":
      return "Input is too quiet.";
    case "good":
      return "Microphone level looks good.";
    case "clipping":
      return "Input is clipping. Move back or reduce gain.";
  }
}

function sleep(durationMs: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, durationMs));
}

function recordingInputQuality(recording: RecordedWav) {
  return {
    peakEnergy: recording.inputQuality.peakEnergy,
    levelCounts: {
      noSignal: recording.inputQuality.levelCounts["no-signal"],
      tooQuiet: recording.inputQuality.levelCounts["too-quiet"],
      good: recording.inputQuality.levelCounts.good,
      clipping: recording.inputQuality.levelCounts.clipping
    }
  };
}

function isUsableFloorNoise(recording: RecordedWav): boolean {
  const levelCounts = recording.inputQuality.levelCounts;
  const total = Object.values(levelCounts).reduce((sum, count) => sum + count, 0);
  if (total === 0 || levelCounts.clipping > 0) {
    return false;
  }
  return levelCounts.good / total < 0.25;
}

function sameContext(
  firstSpeaker: string | undefined,
  firstText: string | undefined,
  secondSpeaker: string | undefined,
  secondText: string | undefined
): boolean {
  if (!firstText || !secondText) {
    return false;
  }
  return firstSpeaker === secondSpeaker && firstText.trim() === secondText.trim();
}
