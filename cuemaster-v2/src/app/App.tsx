import { useMemo, useRef, useState, type ReactNode } from "react";
import type { LoadedPlaybook, Playbook, PlaybookLine, PlaybookRole } from "../domain/playbook";
import { fairiesDemoManifest } from "../fixtures/fairiesDemoManifest";
import { PlaybookZipImporter } from "../playbook/extractPlaybookZip";
import { PlaybookNormalizer } from "../playbook/normalizePlaybook";
import { PlaybackRunner, type PlaybackRunnerStatus } from "../playback/playbackRunner";
import { RoleRehearsalSequenceBuilder, WholePlaySequenceBuilder, type PlaybackStep } from "../playback/playbackSequence";
import { practiceFlowLabels, practiceFlows, type PracticeFlow } from "../practice/practiceFlow";

type Screen = "library" | "setup" | "rehearsal" | "play";

const emptyAudioAssets = new Map<string, Blob>();
const demoLoadedPlaybook: LoadedPlaybook = {
  playbook: new PlaybookNormalizer().normalize(fairiesDemoManifest),
  audioAssets: emptyAudioAssets
};

const defaultStatus: PlaybackRunnerStatus = {
  label: "Ready",
  detail: "Choose Play",
  progress: 0
};

export function App() {
  const [loadedPlaybook, setLoadedPlaybook] = useState<LoadedPlaybook>(demoLoadedPlaybook);
  const [screen, setScreen] = useState<Screen>("library");
  const [selectedRoleId, setSelectedRoleId] = useState("LILLIAN");
  const [flow, setFlow] = useState<PracticeFlow>("manual");
  const [lineIndex, setLineIndex] = useState(0);
  const [playIndex, setPlayIndex] = useState(0);
  const [linePace, setLinePace] = useState(1);
  const [showLine, setShowLine] = useState(false);
  const [showBlocking, setShowBlocking] = useState(true);
  const [sheet, setSheet] = useState<"options" | "navigation" | "blocking" | null>(null);
  const [status, setStatus] = useState(defaultStatus);
  const [playing, setPlaying] = useState(false);
  const [importMessage, setImportMessage] = useState("Fairies demo fixture loaded. Import a real .playbook.zip to enable audio.");
  const runnerRef = useRef<PlaybackRunner | null>(null);

  const playbook = loadedPlaybook.playbook;
  const roles = playbook.roles;
  const selectedRole = roleById(playbook, selectedRoleId) ?? roles[0];
  const currentLine = selectedRole.lines[Math.min(lineIndex, selectedRole.lines.length - 1)];
  const wholePlayItems = useMemo(() => new WholePlaySequenceBuilder().build(playbook), [playbook]);
  const currentPlayItem = wholePlayItems[Math.min(playIndex, wholePlayItems.length - 1)];

  function stopPlayback(nextStatus: PlaybackRunnerStatus = defaultStatus) {
    runnerRef.current?.stop();
    runnerRef.current = null;
    setPlaying(false);
    setStatus(nextStatus);
  }

  async function importPlaybook(file: File) {
    stopPlayback({ label: "Importing", detail: file.name, progress: 10 });
    const imported = await new PlaybookZipImporter().import(file);
    setLoadedPlaybook(imported);
    setSelectedRoleId(imported.playbook.roles[0]?.id ?? "");
    setLineIndex(0);
    setPlayIndex(0);
    setScreen("setup");
    setImportMessage(`${imported.playbook.title} imported with ${imported.playbook.roles.length} roles.`);
    setStatus({ label: "Imported", detail: imported.playbook.title, progress: 100 });
  }

  function runSteps(steps: PlaybackStep[], onDone?: () => void) {
    if (playing) {
      stopPlayback({ label: "Paused", detail: "Tap Play to continue", progress: status.progress });
      return;
    }

    const runner = new PlaybackRunner({
      resolveAudio: (path) => loadedPlaybook.audioAssets.get(path),
      onStatus: setStatus,
      onAdvance: () => {
        if (screen === "play") {
          setPlayIndex((index) => Math.min(index + 1, wholePlayItems.length - 1));
        } else {
          setLineIndex((index) => Math.min(index + 1, selectedRole.lines.length - 1));
        }
      },
      onDone: () => {
        setPlaying(false);
        onDone?.();
      }
    });
    runnerRef.current = runner;
    setPlaying(true);
    void runner.run(steps);
  }

  function runCurrentFlow() {
    if (screen === "play") {
      const steps = wholePlayItems.slice(playIndex).flatMap((item): PlaybackStep[] => {
        if (item.audioPath === undefined) {
          return [{ kind: "wait", label: item.speaker, durationMs: 600 }, { kind: "advance", label: "Next passage" }];
        }
        return [
          { kind: "audio", label: item.speaker, audioPath: item.audioPath, durationMs: item.durationMs },
          { kind: "advance", label: "Next passage" }
        ];
      });
      runSteps(steps, () => setStatus({ label: "Complete", detail: "End of play", progress: 100 }));
      return;
    }

    runSteps(new RoleRehearsalSequenceBuilder().build(currentLine, flow, linePace), () =>
      setStatus(statusForIdle(screen, flow, currentLine, currentPlayItem))
    );
  }

  function runRepeatCue() {
    if (screen === "play") {
      const item = currentPlayItem;
      if (item.audioPath !== undefined) {
        runSteps([{ kind: "audio", label: `Repeat ${item.id}`, audioPath: item.audioPath, durationMs: item.durationMs }]);
      }
      return;
    }
    runSteps([{ kind: "audio", label: `Cue: ${currentLine.cue.speaker}`, audioPath: currentLine.cue.audioPath, durationMs: currentLine.cue.durationMs }]);
  }

  function runHearLine() {
    const steps = currentLine.responseSegments.map(
      (segment): PlaybackStep => ({
        kind: "audio",
        label: "Hear Line",
        audioPath: segment.audioPath,
        durationMs: Math.round(segment.durationMs / linePace)
      })
    );
    runSteps(steps, () => setShowLine(true));
  }

  function changeScreen(nextScreen: Screen) {
    stopPlayback(statusForIdle(nextScreen, flow, currentLine, currentPlayItem));
    setScreen(nextScreen);
  }

  function selectRole(roleId: string) {
    stopPlayback();
    setSelectedRoleId(roleId);
    setLineIndex(0);
  }

  return (
    <main className="app-shell">
      <section className="phone" aria-label="Cuemaster V2">
        <header className="topbar">
          <button className="icon-button" type="button" onClick={() => setSheet("navigation")} aria-label="Navigate">
            <span aria-hidden="true">⌕</span>
          </button>
          <div className="title-block">
            <p className="play-title">{playbook.title}</p>
            <p className="subtitle">{subtitle(screen, selectedRole, flow)}</p>
          </div>
          <span className="position-pill">{screen === "play" ? currentPlayItem?.id : currentLine?.id}</span>
          <button className="icon-button" type="button" onClick={() => setSheet("options")} aria-label="Options">
            <span aria-hidden="true">⚙</span>
          </button>
        </header>

        <div className="content">
          {screen === "library" && (
            <LibraryScreen playbook={playbook} message={importMessage} onImport={importPlaybook} onSetup={() => changeScreen("setup")} onPlay={() => changeScreen("play")} />
          )}
          {screen === "setup" && (
            <SetupScreen
              roles={roles}
              selectedRole={selectedRole}
              flow={flow}
              onRole={selectRole}
              onFlow={setFlow}
              onStart={() => changeScreen("rehearsal")}
            />
          )}
          {screen === "rehearsal" && (
            <RehearsalScreen line={currentLine} flow={flow} linePace={linePace} showLine={showLine} showBlocking={showBlocking} onBlocking={() => setSheet("blocking")} status={statusForDisplay(status, screen, flow, currentLine, currentPlayItem)} />
          )}
          {screen === "play" && (
            <WholePlayScreen
              items={wholePlayItems}
              currentIndex={playIndex}
              showBlocking={showBlocking}
              status={statusForDisplay(status, screen, flow, currentLine, currentPlayItem)}
              onJump={(index) => {
                stopPlayback({ label: "Ready", detail: wholePlayItems[index]?.id ?? "", progress: 0 });
                setPlayIndex(index);
              }}
              onBlocking={(index) => {
                setPlayIndex(index);
                setSheet("blocking");
              }}
            />
          )}
        </div>

        {screen !== "library" && screen !== "setup" && (
          <Transport
            mode={screen}
            playing={playing}
            onPrevious={() => {
              stopPlayback();
              if (screen === "play") {
                setPlayIndex((index) => Math.max(0, index - 1));
              } else {
                setLineIndex((index) => Math.max(0, index - 1));
              }
            }}
            onRepeat={runRepeatCue}
            onPlay={runCurrentFlow}
            onHearLine={runHearLine}
            onNext={() => {
              stopPlayback();
              if (screen === "play") {
                setPlayIndex((index) => Math.min(wholePlayItems.length - 1, index + 1));
              } else {
                setLineIndex((index) => Math.min(selectedRole.lines.length - 1, index + 1));
              }
            }}
          />
        )}

        {sheet !== null && (
          <Sheet onClose={() => setSheet(null)}>
            {sheet === "options" && (
              <OptionsSheet
                flow={flow}
                linePace={linePace}
                showLine={showLine}
                showBlocking={showBlocking}
                onFlow={setFlow}
                onLinePace={setLinePace}
                onShowLine={setShowLine}
                onShowBlocking={setShowBlocking}
              />
            )}
            {sheet === "navigation" && (
              <NavigationSheet
                roles={roles}
                selectedRole={selectedRole}
                lines={selectedRole.lines}
                playItems={wholePlayItems}
                onSetup={() => {
                  setSheet(null);
                  changeScreen("setup");
                }}
                onLine={(index) => {
                  setSheet(null);
                  setLineIndex(index);
                  changeScreen("rehearsal");
                }}
                onPlayItem={(index) => {
                  setSheet(null);
                  setPlayIndex(index);
                  changeScreen("play");
                }}
              />
            )}
            {sheet === "blocking" && <BlockingSheet line={screen === "play" ? undefined : currentLine} playItem={screen === "play" ? currentPlayItem : undefined} playbook={playbook} />}
          </Sheet>
        )}
      </section>
    </main>
  );
}

function LibraryScreen({
  playbook,
  message,
  onImport,
  onSetup,
  onPlay
}: {
  playbook: Playbook;
  message: string;
  onImport: (file: File) => Promise<void>;
  onSetup: () => void;
  onPlay: () => void;
}) {
  return (
    <div className="screen-stack">
      <section className="card">
        <h1>Playbooks</h1>
        <p>{message}</p>
        <label className="file-import">
          <span>Import Playbook Zip</span>
          <input
            type="file"
            accept=".zip,.playbook.zip,application/zip"
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file !== undefined) {
                void onImport(file);
              }
            }}
          />
        </label>
      </section>
      <section className="card playbook-card">
        <h2>{playbook.title}</h2>
        <p>
          {playbook.roles.length} roles. Format {playbook.formatVersion}. {playbook.staging ? "Blocking diagrams available." : "Blocking notes available; diagram bundle not included."}
        </p>
        <div className="button-row">
          <button className="button primary" type="button" onClick={onSetup}>
            Practice Role
          </button>
          <button className="button" type="button" onClick={onPlay}>
            Listen to Play
          </button>
        </div>
      </section>
    </div>
  );
}

function SetupScreen({
  roles,
  selectedRole,
  flow,
  onRole,
  onFlow,
  onStart
}: {
  roles: PlaybookRole[];
  selectedRole: PlaybookRole;
  flow: PracticeFlow;
  onRole: (roleId: string) => void;
  onFlow: (flow: PracticeFlow) => void;
  onStart: () => void;
}) {
  return (
    <div className="screen-stack">
      <section className="card">
        <h1>Choose Role</h1>
        <div className="choice-list">
          {roles.map((role) => (
            <button className={`choice ${role.id === selectedRole.id ? "active" : ""}`} type="button" key={role.id} onClick={() => onRole(role.id)}>
              <strong>{role.displayName}</strong>
              <span>{role.lineCount} lines</span>
            </button>
          ))}
        </div>
      </section>
      <section className="card">
        <h1>Practice Flow</h1>
        <div className="flow-grid">
          {practiceFlows.map((candidate) => (
            <button className={`choice ${candidate === flow ? "active" : ""}`} type="button" key={candidate} onClick={() => onFlow(candidate)}>
              <strong>{practiceFlowLabels[candidate]}</strong>
              <span>{flowDescription(candidate)}</span>
            </button>
          ))}
        </div>
      </section>
      <button className="button primary start-button" type="button" onClick={onStart}>
        Start Practice
      </button>
    </div>
  );
}

function RehearsalScreen({
  line,
  flow,
  linePace,
  showLine,
  showBlocking,
  status,
  onBlocking
}: {
  line: PlaybookLine;
  flow: PracticeFlow;
  linePace: number;
  showLine: boolean;
  showBlocking: boolean;
  status: PlaybackRunnerStatus;
  onBlocking: () => void;
}) {
  return (
    <section className="rehearsal screen-stack">
      <div className="mode-summary">
        <span>{practiceFlowLabels[flow]}</span>
        <span>{linePace.toFixed(1)}x line pace</span>
      </div>
      <article className="card cue-card">
        <h1>Cue: {line.cue.speaker}</h1>
        <p className="cue-text">{line.cue.text}</p>
      </article>
      <article className="card line-card">
        <h1>{line.role}</h1>
        {showLine ? <p className="line-text">{line.responseText}</p> : <p className="hidden-line">Line hidden</p>}
        {showBlocking && line.blocking.length > 0 && (
          <button className="blocking-note" type="button" onClick={onBlocking}>
            {line.blocking.map((blocking) => blocking.text).join(" / ")}
          </button>
        )}
      </article>
      <StatusPill status={status} />
    </section>
  );
}

function WholePlayScreen({
  items,
  currentIndex,
  showBlocking,
  status,
  onJump,
  onBlocking
}: {
  items: ReturnType<WholePlaySequenceBuilder["build"]>;
  currentIndex: number;
  showBlocking: boolean;
  status: PlaybackRunnerStatus;
  onJump: (index: number) => void;
  onBlocking: (index: number) => void;
}) {
  return (
    <section className="whole-play screen-stack">
      <div className="mode-summary">
        <span>Whole Play</span>
        <span>Autoscroll script</span>
      </div>
      <div className="script-scroll" aria-label="Whole play script">
        {items.map((item, index) => (
          <div className={`script-line ${index === currentIndex ? "current" : ""}`} key={`${item.id}-${index}`}>
            <button className="script-line-hit" type="button" onClick={() => onJump(index)}>
              <strong>
                {item.id} · {item.speaker}
              </strong>
              <span>{item.text}</span>
            </button>
            {showBlocking &&
              item.blocking.map((blocking) => (
                <button
                  className="script-blocking"
                  type="button"
                  key={blocking.id}
                  onClick={(event) => {
                    event.stopPropagation();
                    onBlocking(index);
                  }}
                >
                  {blocking.text}
                </button>
              ))}
          </div>
        ))}
      </div>
      <StatusPill status={status} />
    </section>
  );
}

function Transport({
  mode,
  playing,
  onPrevious,
  onRepeat,
  onPlay,
  onHearLine,
  onNext
}: {
  mode: "rehearsal" | "play";
  playing: boolean;
  onPrevious: () => void;
  onRepeat: () => void;
  onPlay: () => void;
  onHearLine: () => void;
  onNext: () => void;
}) {
  return (
    <nav className="transport" aria-label={mode === "play" ? "Whole play controls" : "Rehearsal controls"}>
      <button className="transport-button" type="button" onClick={onPrevious} aria-label="Previous">
        ⏮
      </button>
      <button className="transport-button" type="button" onClick={onRepeat} aria-label="Repeat">
        ↻
      </button>
      <button className="transport-button primary" type="button" onClick={onPlay} aria-label={playing ? "Pause" : "Play"}>
        {playing ? "⏸" : "▶"}
      </button>
      <button className="transport-button" type="button" onClick={onHearLine} aria-label="Hear line" disabled={mode === "play"}>
        ◉
      </button>
      <button className="transport-button" type="button" onClick={onNext} aria-label="Next">
        ⏭
      </button>
    </nav>
  );
}

function StatusPill({ status }: { status: PlaybackRunnerStatus }) {
  return (
    <section className="status-pill" aria-live="polite">
      <div>
        <strong>{status.label}</strong>
        <span>{status.detail}</span>
      </div>
      <div className="progress">
        <span style={{ width: `${status.progress}%` }} />
      </div>
    </section>
  );
}

function OptionsSheet({
  flow,
  linePace,
  showLine,
  showBlocking,
  onFlow,
  onLinePace,
  onShowLine,
  onShowBlocking
}: {
  flow: PracticeFlow;
  linePace: number;
  showLine: boolean;
  showBlocking: boolean;
  onFlow: (flow: PracticeFlow) => void;
  onLinePace: (pace: number) => void;
  onShowLine: (show: boolean) => void;
  onShowBlocking: (show: boolean) => void;
}) {
  return (
    <>
      <h1>Options</h1>
      <section className="sheet-section">
        <h2>Practice Flow</h2>
        <div className="flow-grid">
          {practiceFlows.map((candidate) => (
            <button className={`choice ${candidate === flow ? "active" : ""}`} type="button" key={candidate} onClick={() => onFlow(candidate)}>
              <strong>{practiceFlowLabels[candidate]}</strong>
              <span>{flowDescription(candidate)}</span>
            </button>
          ))}
        </div>
      </section>
      <section className="sheet-section">
        <h2>Line Pace</h2>
        <div className="button-row">
          {[0.8, 0.9, 1, 1.1, 1.2].map((pace) => (
            <button className={`button ${linePace === pace ? "active" : ""}`} type="button" key={pace} onClick={() => onLinePace(pace)}>
              {pace.toFixed(1)}x
            </button>
          ))}
        </div>
      </section>
      <section className="sheet-section">
        <h2>Display</h2>
        <label className="check-row">
          <input type="checkbox" checked={showLine} onChange={(event) => onShowLine(event.currentTarget.checked)} />
          <span>Show my lines by default</span>
        </label>
        <label className="check-row">
          <input type="checkbox" checked={showBlocking} onChange={(event) => onShowBlocking(event.currentTarget.checked)} />
          <span>Show blocking notes</span>
        </label>
      </section>
      <section className="sheet-section muted">
        <h2>iOS</h2>
        <p>Tempo timing is hidden on iOS. These flows avoid microphone setup and can run after a single Play tap.</p>
      </section>
    </>
  );
}

function NavigationSheet({
  roles,
  selectedRole,
  lines,
  playItems,
  onSetup,
  onLine,
  onPlayItem
}: {
  roles: PlaybookRole[];
  selectedRole: PlaybookRole;
  lines: PlaybookLine[];
  playItems: ReturnType<WholePlaySequenceBuilder["build"]>;
  onSetup: () => void;
  onLine: (index: number) => void;
  onPlayItem: (index: number) => void;
}) {
  return (
    <>
      <h1>Navigate</h1>
      <button className="button" type="button" onClick={onSetup}>
        Role setup ({roles.length} roles)
      </button>
      <section className="sheet-section">
        <h2>{selectedRole.displayName}</h2>
        <div className="nav-list">
          {lines.map((line, index) => (
            <button className="nav-item" type="button" key={line.id} onClick={() => onLine(index)}>
              <strong>{line.id}</strong>
              <span>{line.cue.speaker}: {line.cue.text}</span>
            </button>
          ))}
        </div>
      </section>
      <section className="sheet-section">
        <h2>Whole Play</h2>
        <div className="nav-list">
          {playItems.map((item, index) => (
            <button className="nav-item" type="button" key={`${item.id}-${index}`} onClick={() => onPlayItem(index)}>
              <strong>{item.id} · {item.speaker}</strong>
              <span>{item.text}</span>
            </button>
          ))}
        </div>
      </section>
    </>
  );
}

function BlockingSheet({ line, playItem, playbook }: { line?: PlaybookLine; playItem?: ReturnType<WholePlaySequenceBuilder["build"]>[number]; playbook: Playbook }) {
  const notes =
    line?.blocking.map((blocking) => ({ id: blocking.id, text: blocking.text })) ??
    playItem?.blocking ??
    [];
  return (
    <>
      <h1>{line?.id ?? playItem?.id} Blocking</h1>
      {notes.length === 0 ? <p>No blocking notes for this position.</p> : notes.map((note) => <p className="blocking-detail" key={note.id}>{note.text}</p>)}
      <div className="diagram-placeholder">
        {playbook.staging ? "Diagram bundle hook is available." : "This playbook has blocking notes but no diagram bundle."}
      </div>
    </>
  );
}

function Sheet({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  return (
    <div className="sheet-backdrop" role="presentation" onClick={onClose}>
      <section className="sheet" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <button className="sheet-close" type="button" onClick={onClose} aria-label="Close">
          ×
        </button>
        {children}
      </section>
    </div>
  );
}

function statusForIdle(screen: Screen, flow: PracticeFlow, line: PlaybookLine, playItem?: ReturnType<WholePlaySequenceBuilder["build"]>[number]): PlaybackRunnerStatus {
  if (screen === "play") {
    return { label: "Ready", detail: playItem?.id ?? "Whole Play", progress: 0 };
  }
  if (flow === "listen") {
    return { label: "Ready to listen", detail: line.id, progress: 0 };
  }
  if (flow === "try") {
    return { label: "Ready to try", detail: line.id, progress: 0 };
  }
  if (flow === "try_then_check") {
    return { label: "Ready to try + hear", detail: line.id, progress: 0 };
  }
  return { label: "Ready for cue", detail: line.id, progress: 0 };
}

function statusForDisplay(status: PlaybackRunnerStatus, screen: Screen, flow: PracticeFlow, line: PlaybookLine, playItem?: ReturnType<WholePlaySequenceBuilder["build"]>[number]): PlaybackRunnerStatus {
  if (status.label === "Ready") {
    return statusForIdle(screen, flow, line, playItem);
  }
  return status;
}

function subtitle(screen: Screen, role: PlaybookRole, flow: PracticeFlow): string {
  if (screen === "library") {
    return "Library";
  }
  if (screen === "setup") {
    return "Role setup";
  }
  if (screen === "play") {
    return "Whole Play";
  }
  return `${role.displayName} · ${practiceFlowLabels[flow]}`;
}

function roleById(playbook: Playbook, roleId: string): PlaybookRole | undefined {
  return playbook.roles.find((role) => role.id === roleId);
}

function flowDescription(flow: PracticeFlow): string {
  if (flow === "listen") {
    return "Cue and line continuously.";
  }
  if (flow === "try") {
    return "Cue, then give me time.";
  }
  if (flow === "try_then_check") {
    return "Cue, wait, then play my line.";
  }
  return "Cue, then wait for me.";
}
