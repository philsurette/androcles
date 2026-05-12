import { useEffect, useRef, useState } from "react";
import { MicrophoneSession, type MicrophoneReading } from "../audio/microphoneSession";
import { meterFillPercentForLevel } from "../audio/inputMeter";
import { WavRecorder, type RecordedWav, type WavRecorderReading } from "../audio/wavRecorder";
import type { RecordingItem } from "../domain/recordingItem";
import { recordingItemProgress, type RecordingItemProgress } from "../domain/recordingItemStatus";
import { nextProgress, previousProgress, selectedProgressIndex } from "../domain/recordingNavigation";
import type { RecordingTake } from "../domain/take";
import { exportRoleRecordings, RoleRecordingsExportError } from "../package/exportRoleRecordings";
import { importRecordingRequest, RecordingRequestImportError } from "../package/importRecordingRequest";
import { listMicrophoneDevices, MicrophonePermissionError, type MicrophoneDevice, type MicrophoneMode } from "../platform/microphone";
import { projectRepository } from "../storage/projectRepository";
import { takeRepository } from "../storage/takeRepository";
import type { RecordingProjectRecord } from "../storage/db";

export function App() {
  const [projects, setProjects] = useState<RecordingProjectRecord[]>([]);
  const [selectedProject, setSelectedProject] = useState<RecordingProjectRecord | null>(null);
  const [acceptedSegmentIds, setAcceptedSegmentIds] = useState<Set<string>>(new Set());
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

  async function exportProject(project: RecordingProjectRecord): Promise<void> {
    setIsExporting(true);
    setStatus("Exporting role recordings...");
    try {
      const acceptedTakes = await takeRepository.acceptedForProject(project.id);
      const exported = await exportRoleRecordings(project, acceptedTakes);
      downloadBlob(exported.blob, exported.fileName);
      const exportedCount = exported.manifest.recordings.length;
      const missingCount = exported.manifest.missing_segment_ids.length;
      setStatus(
        exported.manifest.complete
          ? `Exported complete role recordings package with ${exportedCount} recordings.`
          : `Exported partial role recordings package with ${exportedCount} recordings; ${missingCount} still missing.`
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
    }
    await loadProjects();
    setStatus(`Deleted local recordings for ${project.request.role.displayName}.`);
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
          onAccepted={() => loadAcceptedSegments(selectedProject.id)}
          onExport={() => void exportProject(selectedProject)}
          onDelete={() => void deleteProject(selectedProject)}
          isExporting={isExporting}
        />
      ) : (
        <ProjectLibrary
          projects={projects}
          onOpenProject={(project) => void openProject(project)}
          onDeleteProject={(project) => void deleteProject(project)}
        />
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
              <button type="button" className="secondary danger" onClick={() => onDeleteProject(project)}>
                Delete
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
  acceptedSegmentIds: Set<string>;
  onSelectItem: (item: RecordingItem) => void;
  onAccepted: () => Promise<void>;
  onExport: () => void;
  onDelete: () => void;
  isExporting: boolean;
};

function ProjectDetail({
  project,
  acceptedSegmentIds,
  onSelectItem,
  onAccepted,
  onExport,
  onDelete,
  isExporting
}: ProjectDetailProps) {
  const [microphoneConfig, setMicrophoneConfig] = useState<MicrophoneConfig | null>(null);
  const progress = recordingItemProgress(project.request.items, acceptedSegmentIds);
  const selectedIndex = selectedProgressIndex(progress, project.currentSegmentId);
  const selectedItem = selectedIndex === -1 ? undefined : progress[selectedIndex];
  const previousItem = previousProgress(progress, selectedIndex);
  const nextItem = nextProgress(progress, selectedIndex);

  return (
    <section className="project-detail" aria-label="Recording Request detail">
      <ProjectSummary
        project={project}
        progress={progress}
        onExport={onExport}
        onDelete={onDelete}
        isExporting={isExporting}
      />
      <MicrophoneSetup onReady={setMicrophoneConfig} />
      <div className="recording-workspace">
        <ItemList progress={progress} selectedSegmentId={selectedItem?.item.segmentId} onSelectItem={onSelectItem} />
        {selectedItem ? (
          <ItemDetail
            project={project}
            progress={selectedItem}
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
  mode: MicrophoneMode;
};

type MicrophoneSetupProps = {
  onReady: (config: MicrophoneConfig | null) => void;
};

function MicrophoneSetup({ onReady }: MicrophoneSetupProps) {
  const sessionRef = useRef<MicrophoneSession | null>(null);
  const [devices, setDevices] = useState<MicrophoneDevice[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [mode, setMode] = useState<MicrophoneMode>("clean");
  const [reading, setReading] = useState<MicrophoneReading>({ energy: 0, level: "no-signal" });
  const [status, setStatus] = useState("Microphone not started.");
  const [isActive, setIsActive] = useState(false);

  useEffect(() => {
    return () => {
      sessionRef.current?.stop();
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
      onReady({ deviceId: selectedDeviceId, mode });
      setIsActive(true);
    } catch (error) {
      const message =
        error instanceof MicrophonePermissionError ? error.message : "Unable to start microphone setup.";
      setStatus(message);
      setIsActive(false);
    }
  }

  function stopMicrophone(): void {
    sessionRef.current?.stop();
    sessionRef.current = null;
    onReady(null);
    setIsActive(false);
    setReading({ energy: 0, level: "no-signal" });
    setStatus("Microphone stopped.");
  }

  return (
    <section className="microphone-panel" aria-label="Microphone setup">
      <div>
        <p className="eyebrow">Microphone</p>
        <h2>Setup</h2>
      </div>
      <div className="microphone-controls">
        <label>
          Input
          <select
            value={selectedDeviceId}
            disabled={isActive}
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
          Mode
          <select
            value={mode}
            disabled={isActive}
            onChange={(event) => setMode(event.target.value as MicrophoneMode)}
          >
            <option value="clean">Clean room</option>
            <option value="noisy">Noisy room</option>
          </select>
        </label>
        {isActive ? (
          <button type="button" className="secondary" onClick={stopMicrophone}>
            Stop Mic
          </button>
        ) : (
          <button type="button" onClick={() => void startMicrophone()}>
            Start Setup
          </button>
        )}
      </div>
      <div className="meter-row">
        <div className="meter" aria-label={`Input level: ${levelLabel(reading.level)}`}>
          <span style={{ width: `${meterFillPercentForLevel(reading.energy, reading.level)}%` }} />
        </div>
        <span className={`meter-label ${reading.level}`}>{levelLabel(reading.level)}</span>
      </div>
      <p className="microphone-status">{status}</p>
    </section>
  );
}

type ProjectSummaryProps = {
  project: RecordingProjectRecord;
  progress: RecordingItemProgress[];
  onExport: () => void;
  onDelete: () => void;
  isExporting: boolean;
};

function ProjectSummary({ project, progress, onExport, onDelete, isExporting }: ProjectSummaryProps) {
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
      <div className="summary-actions">
        <button type="button" className="secondary danger" onClick={onDelete}>
          Delete Project
        </button>
        <button type="button" disabled={acceptedCount === 0 || isExporting} onClick={onExport}>
          {isExporting ? "Exporting..." : "Export Recordings"}
        </button>
      </div>
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
  project: RecordingProjectRecord;
  progress: RecordingItemProgress;
  microphoneConfig: MicrophoneConfig | null;
  previousItem: RecordingItemProgress | undefined;
  nextItem: RecordingItemProgress | undefined;
  onNavigate: (item: RecordingItem) => void;
  onAccepted: () => Promise<void>;
};

function ItemDetail({ project, progress, microphoneConfig, previousItem, nextItem, onNavigate, onAccepted }: ItemDetailProps) {
  const { item, status } = progress;
  const showPrevious = !sameContext(item.previousSpeaker, item.previousText, item.cueSpeaker, item.cueText);
  return (
    <article className="item-detail">
      <header>
        <p className="eyebrow">{item.sectionTitle ?? "Recording Item"}</p>
        <div className="item-heading">
          <h2>Line {item.sequence}</h2>
          <span className={status === "accepted" ? "status-pill accepted" : "status-pill"}>{status}</span>
        </div>
        <div className="line-navigation" aria-label="Line navigation">
          <button
            type="button"
            className="secondary"
            disabled={!previousItem}
            onClick={() => previousItem && onNavigate(previousItem.item)}
          >
            Previous
          </button>
          <button
            type="button"
            className="secondary"
            disabled={!nextItem}
            onClick={() => nextItem && onNavigate(nextItem.item)}
          >
            Next
          </button>
        </div>
      </header>

      <ContextBlock label="Cue" speaker={item.cueSpeaker} text={item.cueText} />
      {showPrevious ? <ContextBlock label="Previous" speaker={item.previousSpeaker} text={item.previousText} /> : null}

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
      <TakeRecorder project={project} item={item} microphoneConfig={microphoneConfig} onAccepted={onAccepted} />
    </article>
  );
}

type TakeRecorderProps = {
  project: RecordingProjectRecord;
  item: RecordingItem;
  microphoneConfig: MicrophoneConfig | null;
  onAccepted: () => Promise<void>;
};

function TakeRecorder({ project, item, microphoneConfig, onAccepted }: TakeRecorderProps) {
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
  }, [item.segmentId]);

  useEffect(() => {
    if (microphoneConfig && statusTone === "warning" && status === "Start microphone setup before recording.") {
      setStatus(currentTake ? "Ready to accept or retry take." : acceptedTake ? `Accepted take saved: ${Math.round(acceptedTake.durationMs)} ms.` : "Ready to record.");
      setStatusTone("normal");
    }
  }, [microphoneConfig, status, statusTone, currentTake, acceptedTake]);

  async function loadAcceptedTake(): Promise<void> {
    const take = await takeRepository.acceptedForSegment(project.id, item.segmentId);
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
      id: `${project.id}:${item.segmentId}:${new Date().toISOString()}`,
      projectId: project.id,
      segmentId: item.segmentId,
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

  function retryTake(): void {
    setCurrentTake(null);
    setRecordingReading({ energy: 0, level: "no-signal" });
    setStatus("No take recorded.");
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
      <div>
        <p className="eyebrow">Take</p>
        <p className={statusTone === "warning" ? "take-status warning" : "take-status"}>{status}</p>
      </div>
      <div className="take-controls">
        {isRecording ? (
          <button type="button" onClick={stopRecording}>
            Stop
          </button>
        ) : (
          <button type="button" onClick={() => void startRecording()}>
            Record
          </button>
        )}
        {playingSource === "take" ? (
          <button type="button" className="secondary" onClick={stopPlayback}>
            Stop
          </button>
        ) : (
          <button type="button" className="secondary" disabled={!currentTake || isRecording || Boolean(playingSource)} onClick={playTake}>
            Play Take
          </button>
        )}
        <button type="button" className="secondary" disabled={!currentTake || isRecording} onClick={() => void acceptTake()}>
          Accept
        </button>
        {playingSource === "saved" ? (
          <button type="button" className="secondary" onClick={stopPlayback}>
            Stop
          </button>
        ) : (
          <button type="button" className="secondary" disabled={!acceptedTake || isRecording || Boolean(playingSource)} onClick={playAcceptedTake}>
            Play Saved
          </button>
        )}
        <button type="button" className="secondary" disabled={!currentTake || isRecording} onClick={retryTake}>
          Retry
        </button>
      </div>
      {isRecording ? (
        <div className="meter-row take-meter">
          <div className="meter" aria-label={`Recording input level: ${levelLabel(recordingReading.level)}`}>
            <span style={{ width: `${meterFillPercentForLevel(recordingReading.energy, recordingReading.level)}%` }} />
          </div>
          <span className={`meter-label ${recordingReading.level}`}>{levelLabel(recordingReading.level)}</span>
        </div>
      ) : null}
    </section>
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

function downloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
