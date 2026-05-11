import { useEffect, useState } from "react";
import type { Bookmark } from "../../domain/bookmark";
import type { Line } from "../../domain/line";
import type { Playbook } from "../../domain/playbook";
import type { Role } from "../../domain/role";
import type { RehearsalSession } from "../../domain/session";
import type { TimingAttempt } from "../../domain/timingAttempt";
import { AudioQueue } from "../../rehearsal/audioQueue";
import { shortcutForKey } from "../../rehearsal/keyboardShortcuts";
import { cuePlaybackItems, responsePlaybackItems, speakAlongPlaybackItems } from "../../rehearsal/playbackItems";
import { RehearsalEngine } from "../../rehearsal/rehearsalEngine";
import { scriptBrowserSections } from "../../rehearsal/scriptBrowser";
import { tempoFeedbackFor, type TempoFeedback } from "../../rehearsal/tempoFeedback";
import { VoiceActivityDetector } from "../../rehearsal/voiceActivityDetector";
import type { VoiceActivityResult } from "../../rehearsal/voiceActivityTracker";
import { bookmarkRepository } from "../../storage/bookmarkRepository";
import { sessionRepository } from "../../storage/sessionRepository";
import { timingAttemptRepository } from "../../storage/timingAttemptRepository";
import { CueCard } from "../components/CueCard";
import { LineCard } from "../components/LineCard";

type RehearsalScreenProps = {
  playbook: Playbook;
  role: Role;
  initialSession: RehearsalSession | null;
  onBack: () => void;
};

export function RehearsalScreen({ playbook, role, initialSession, onBack }: RehearsalScreenProps) {
  const [engine] = useState(() =>
    RehearsalEngine.forRole(playbook, role.id, {
      startLineId: role.lines[initialSession?.lineIndex ?? 0]?.id,
      includeDirections: initialSession?.includeDirections
    })
  );
  const [audioQueue] = useState(() => new AudioQueue(playbook.id));
  const [position, setPosition] = useState(() => engine.position());
  const [playbackRate, setPlaybackRate] = useState(clampPlaybackRate(initialSession?.playbackRate ?? 1));
  const [playbackStatus, setPlaybackStatus] = useState<string>("");
  const [isLineRevealed, setIsLineRevealed] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [speakAlongEnabled, setSpeakAlongEnabled] = useState(initialSession?.speakAlongEnabled ?? false);
  const [tempoTimingEnabled, setTempoTimingEnabled] = useState(false);
  const [tempoTimingPreferred, setTempoTimingPreferred] = useState(initialSession?.tempoTimingPreferred ?? false);
  const [tempoStatus, setTempoStatus] = useState<string>(
    initialSession?.tempoTimingPreferred
      ? "Tempo timing was enabled last session. Enable it again to use the microphone."
      : ""
  );
  const [tempoFeedback, setTempoFeedback] = useState<TempoFeedback | null>(null);
  const [lastTimingAttempt, setLastTimingAttempt] = useState<TimingAttempt | null>(null);
  const [recentTimingAttempts, setRecentTimingAttempts] = useState<TimingAttempt[]>([]);
  const [reviewAttempts, setReviewAttempts] = useState<TimingAttempt[]>([]);
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [isCurrentLineBookmarked, setIsCurrentLineBookmarked] = useState(false);
  const [isScriptBrowserOpen, setIsScriptBrowserOpen] = useState(false);
  const [isTempoReviewOpen, setIsTempoReviewOpen] = useState(false);
  const [voiceActivityDetector, setVoiceActivityDetector] = useState<VoiceActivityDetector | null>(null);
  const line = engine.currentLine();
  const cues = engine.cuePayloads();

  useEffect(() => {
    void saveSession(engine.position().index);
  }, []);

  useEffect(() => {
    return () => {
      voiceActivityDetector?.stop();
    };
  }, [voiceActivityDetector]);

  useEffect(() => {
    void loadLastTimingAttempt();
    void loadCurrentBookmark();
  }, [line?.id]);

  useEffect(() => {
    void loadBookmarks();
  }, []);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const shortcut = shortcutForKey(event);
      if (!shortcut) {
        return;
      }
      event.preventDefault();
      if (shortcut === "repeat-cue") {
        void playCue();
      } else if (shortcut === "next" && !engine.position().atEnd) {
        void goNext();
      } else if (shortcut === "previous" && !engine.position().atBeginning) {
        void goPrevious();
      } else if (shortcut === "hear-line" && engine.currentLine()) {
        void playResponse();
      } else if (shortcut === "stop") {
        stopPlayback();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  async function goNext() {
    engine.next();
    updatePosition();
    setIsLineRevealed(false);
    if (hasStarted) {
      await playCue();
    }
  }

  async function jumpToLine(lineId: string) {
    const targetLine = role.lines.find((candidate) => candidate.id === lineId);
    if (!targetLine) {
      throw new Error(`Line not found for role ${role.id}: ${lineId}`);
    }
    while (engine.currentLine()?.id !== lineId && !engine.position().atEnd) {
      engine.next();
    }
    while (engine.currentLine()?.id !== lineId && !engine.position().atBeginning) {
      engine.previous();
    }
    updatePosition();
    setIsLineRevealed(false);
    setIsScriptBrowserOpen(false);
    setIsTempoReviewOpen(false);
  }

  async function goPrevious() {
    engine.previous();
    updatePosition();
    setIsLineRevealed(false);
    if (hasStarted) {
      await playCue();
    }
  }

  function updatePosition() {
    const nextPosition = engine.position();
    setPosition(nextPosition);
    setTempoFeedback(null);
    void saveSession(nextPosition.index, playbackRate);
  }

  async function saveSession(
    lineIndex: number,
    nextPlaybackRate = playbackRate,
    nextSpeakAlongEnabled = speakAlongEnabled,
    nextTempoTimingPreferred = tempoTimingPreferred
  ) {
    await sessionRepository.save({
      playbookId: playbook.id,
      roleId: role.id,
      lineIndex,
      includeDirections: engine.includeDirections(),
      playbackRate: nextPlaybackRate,
      speakAlongEnabled: nextSpeakAlongEnabled,
      tempoTimingPreferred: nextTempoTimingPreferred,
      updatedAt: Date.now()
    });
  }

  async function playCue() {
    setHasStarted(true);
    setPlaybackStatus("Playing cue...");
    try {
      await audioQueue.play(cuePlaybackItems(engine.cuePayloads()));
      setPlaybackStatus("Cue complete.");
      beginTimedAttempt();
    } catch (error) {
      setPlaybackStatus(error instanceof Error ? error.message : "Cue playback failed.");
    }
  }

  async function playResponse() {
    if (!line) {
      return;
    }
    setPlaybackStatus("Playing your line...");
    try {
      await audioQueue.play(responsePlaybackItems(line, playbackRate));
      setPlaybackStatus("Line complete.");
    } catch (error) {
      setPlaybackStatus(error instanceof Error ? error.message : "Line playback failed.");
    }
  }

  async function speakAlong() {
    if (!line) {
      return;
    }
    setHasStarted(true);
    setPlaybackStatus("Speak along: playing cue, then your line...");
    try {
      await audioQueue.play(speakAlongPlaybackItems(cues, line, playbackRate));
      setPlaybackStatus("Speak-along complete.");
    } catch (error) {
      setPlaybackStatus(error instanceof Error ? error.message : "Speak-along playback failed.");
    }
  }

  function stopPlayback() {
    audioQueue.cancel();
    setPlaybackStatus("Playback stopped.");
    setTempoStatus(tempoTimingEnabled ? "Tempo timing is idle." : tempoStatus);
  }

  function changePlaybackRate(nextPlaybackRate: number) {
    const clampedPlaybackRate = clampPlaybackRate(nextPlaybackRate);
    setPlaybackRate(clampedPlaybackRate);
    void saveSession(position.index, clampedPlaybackRate);
  }

  function slowDownResponse() {
    changePlaybackRate(playbackRate - playbackRateStep);
  }

  function speedUpResponse() {
    changePlaybackRate(playbackRate + playbackRateStep);
  }

  function resetResponseSpeed() {
    changePlaybackRate(defaultPlaybackRate);
  }

  function changeSpeakAlongEnabled(nextSpeakAlongEnabled: boolean) {
    setSpeakAlongEnabled(nextSpeakAlongEnabled);
    if (nextSpeakAlongEnabled && tempoTimingEnabled) {
      void disableTempoTiming("Tempo timing disabled while speak-along practice is enabled.");
    }
    if (nextSpeakAlongEnabled) {
      setTempoTimingPreferred(false);
    }
    void saveSession(position.index, playbackRate, nextSpeakAlongEnabled, nextSpeakAlongEnabled ? false : tempoTimingPreferred);
  }

  async function enableTempoTiming() {
    setTempoStatus("Requesting microphone permission...");
    const detector = new VoiceActivityDetector(handleVoiceActivity);

    try {
      await detector.start();
      voiceActivityDetector?.stop();
      setVoiceActivityDetector(detector);
      setTempoTimingEnabled(true);
      setTempoTimingPreferred(true);
      setSpeakAlongEnabled(false);
      setTempoStatus("Tempo timing enabled. Press Start or Repeat Cue to time an attempt.");
      await saveSession(position.index, playbackRate, false, true);
    } catch (error) {
      detector.stop();
      setTempoTimingEnabled(false);
      setTempoStatus(error instanceof Error ? error.message : "Could not enable tempo timing.");
    }
  }

  async function disableTempoTiming(message = "Tempo timing disabled."): Promise<void> {
    voiceActivityDetector?.stop();
    setVoiceActivityDetector(null);
    setTempoTimingEnabled(false);
    setTempoTimingPreferred(false);
    setTempoStatus(message);
    await saveSession(position.index, playbackRate, speakAlongEnabled, false);
  }

  function beginTimedAttempt() {
    if (!tempoTimingEnabled || !voiceActivityDetector) {
      return;
    }
    setTempoFeedback(null);
    setTempoStatus("Listening for your pickup...");
    voiceActivityDetector.beginAttempt();
  }

  function handleVoiceActivity(result: VoiceActivityResult) {
    if (!line) {
      return;
    }
    if (result.event === "speech-started") {
      const hesitationMs = Math.round(result.hesitationMs ?? 0);
      setTempoStatus(`Pickup detected after ${hesitationMs} ms. Continue speaking; pause when finished.`);
    } else {
      const hesitationMs = Math.round(result.hesitationMs ?? 0);
      const deliveryMs = Math.round(result.deliveryMs ?? 0);
      const feedback = tempoFeedbackFor(line, { hesitationMs, deliveryMs });
      setTempoFeedback(feedback);
      void saveTimingAttempt(line.id, feedback);
      setTempoStatus("Timed attempt complete.");
    }
  }

  async function saveTimingAttempt(lineId: string, feedback: TempoFeedback) {
    if (!feedback.delivery) {
      return;
    }
    const attempt: TimingAttempt = {
      id: crypto.randomUUID(),
      playbookId: playbook.id,
      roleId: role.id,
      lineId,
      createdAt: Date.now(),
      hesitationMs: feedback.hesitation.measuredMs,
      deliveryMs: feedback.delivery.measuredMs,
      targetHesitationMs: feedback.hesitation.targetMs,
      targetDeliveryMs: feedback.delivery.targetMs,
      hesitationLabel: feedback.hesitation.label,
      deliveryLabel: feedback.delivery.label,
      detectionMode: "energy"
    };
    await timingAttemptRepository.save(attempt);
    setLastTimingAttempt(attempt);
    await loadRecentTimingAttempts();
    await loadReviewAttempts();
  }

  async function loadLastTimingAttempt() {
    if (!line) {
      setLastTimingAttempt(null);
      return;
    }
    setLastTimingAttempt((await timingAttemptRepository.latestForLine(playbook.id, role.id, line.id)) ?? null);
    await loadRecentTimingAttempts();
  }

  async function loadRecentTimingAttempts() {
    if (!line) {
      setRecentTimingAttempts([]);
      return;
    }
    setRecentTimingAttempts(await timingAttemptRepository.recentForLine(playbook.id, role.id, line.id, 5));
  }

  async function loadReviewAttempts() {
    setReviewAttempts(await timingAttemptRepository.latestForRole(playbook.id, role.id));
  }

  async function loadCurrentBookmark() {
    if (!line) {
      setIsCurrentLineBookmarked(false);
      return;
    }
    setIsCurrentLineBookmarked(Boolean(await bookmarkRepository.get(playbook.id, role.id, line.id)));
  }

  async function loadBookmarks() {
    setBookmarks(await bookmarkRepository.listForRole(playbook.id, role.id));
  }

  async function toggleBookmark() {
    if (!line) {
      return;
    }
    if (isCurrentLineBookmarked) {
      await bookmarkRepository.delete(playbook.id, role.id, line.id);
      setIsCurrentLineBookmarked(false);
    } else {
      await bookmarkRepository.save({
        id: `${playbook.id}:${role.id}:${line.id}`,
        playbookId: playbook.id,
        roleId: role.id,
        lineId: line.id,
        createdAt: Date.now()
      });
      setIsCurrentLineBookmarked(true);
    }
    await loadBookmarks();
  }

  async function toggleTempoReview() {
    const nextIsOpen = !isTempoReviewOpen;
    setIsTempoReviewOpen(nextIsOpen);
    if (nextIsOpen) {
      await loadReviewAttempts();
    }
  }

  return (
    <main className="shell">
      <section className="hero rehearsal">
        <button type="button" className="secondary" onClick={onBack}>
          Back to Roles
        </button>
        <header className="rehearsal-header">
          <p className="breadcrumb">
            {playbook.title} / {role.displayName}
          </p>
          <p className="line-position">
            Line {position.total === 0 ? 0 : position.index + 1} of {position.total}
          </p>
        </header>

        {line ? (
          <div className="rehearsal-grid">
            <section className="stack" aria-label="Cue">
              <h2>Cue</h2>
              {cues.map((cue, index) => (
                <CueCard cue={cue} key={`${line.id}-cue-${index}`} />
              ))}
            </section>

            <section className="stack" aria-label="Your Line">
              <h2>Your Line</h2>
              {isLineRevealed ? <LineCard line={line} /> : <article className="card hidden-line">Line hidden</article>}
            </section>
          </div>
        ) : (
          <p className="empty">This role has no rehearsable lines.</p>
        )}

        <div className="transport">
          <button type="button" aria-label="Start or repeat cue. Shortcut: Space or R." onClick={() => void playCue()}>
            {hasStarted ? "Repeat Cue" : "Start"}
          </button>
          <button
            type="button"
            className="secondary"
            aria-label="Go to previous line. Shortcut: Left arrow."
            disabled={position.atBeginning}
            onClick={() => void goPrevious()}
          >
            Previous
          </button>
          <button
            type="button"
            className="secondary"
            aria-label={isLineRevealed ? "Hide your line." : "Reveal your line."}
            disabled={!line}
            onClick={() => setIsLineRevealed(!isLineRevealed)}
          >
            {isLineRevealed ? "Hide Line" : "Reveal Line"}
          </button>
          <button
            type="button"
            className="secondary"
            aria-label={isCurrentLineBookmarked ? "Remove bookmark from current line." : "Bookmark current line."}
            disabled={!line}
            onClick={() => void toggleBookmark()}
          >
            {isCurrentLineBookmarked ? "Remove Bookmark" : "Bookmark"}
          </button>
          <button
            type="button"
            aria-label="Hear your line. Shortcut: L."
            onClick={() => void playResponse()}
            disabled={!line}
          >
            Hear My Line
          </button>
          <button type="button" aria-label="Speak along with the reference line." onClick={() => void speakAlong()} disabled={!line}>
            Speak Along
          </button>
          <button
            type="button"
            aria-label="Go to next line. Shortcut: Right arrow."
            disabled={position.atEnd}
            onClick={() => void goNext()}
          >
            Next
          </button>
          <button type="button" className="secondary" aria-label="Stop playback. Shortcut: Escape." onClick={stopPlayback}>
            Stop
          </button>
        </div>

        <div className="session-settings">
          <label className="check-setting">
            <input
              type="checkbox"
              checked={speakAlongEnabled}
              disabled={tempoTimingEnabled}
              onChange={(event) => changeSpeakAlongEnabled(event.target.checked)}
            />
            Speak-along practice
          </label>
          <label className="check-setting">
            <input
              type="checkbox"
              checked={tempoTimingEnabled}
              onChange={(event) => {
                if (event.target.checked) {
                  void enableTempoTiming();
                } else {
                  void disableTempoTiming();
                }
              }}
            />
            Enable Tempo Timing
          </label>
          <p className="status">
            Tempo timing uses microphone energy only: no recording, no transcription, no upload.
          </p>
          <label>
            Response speed
            <select
              value={playbackRate}
              onChange={(event) => changePlaybackRate(Number(event.target.value))}
            >
              {playbackRates.map((rate) => (
                <option key={rate} value={rate}>
                  {rate.toFixed(1)}x
                </option>
              ))}
            </select>
          </label>
          <div className="speed-controls" aria-label="Response speed quick controls">
            <button type="button" className="secondary" onClick={slowDownResponse} disabled={playbackRate <= minPlaybackRate}>
              Slower
            </button>
            <button type="button" className="secondary" onClick={resetResponseSpeed} disabled={playbackRate === defaultPlaybackRate}>
              Normal
            </button>
            <button type="button" className="secondary" onClick={speedUpResponse} disabled={playbackRate >= maxPlaybackRate}>
              Faster
            </button>
          </div>
          {speakAlongEnabled ? <p className="status">Speak Along plays the cue, then your line at response speed.</p> : null}
          {tempoStatus ? <p className="status">{tempoStatus}</p> : null}
          {tempoFeedback ? <TempoFeedbackPanel feedback={tempoFeedback} /> : null}
          {!tempoFeedback && lastTimingAttempt ? <TimingAttemptPanel attempt={lastTimingAttempt} /> : null}
          {recentTimingAttempts.length > 1 ? <RecentAttemptsPanel attempts={recentTimingAttempts} /> : null}
          {playbackStatus ? <p className="status">{playbackStatus}</p> : null}
          <button type="button" className="secondary" onClick={() => setIsScriptBrowserOpen(!isScriptBrowserOpen)}>
            {isScriptBrowserOpen ? "Hide Script" : "Browse Script"}
          </button>
          <button type="button" className="secondary" onClick={() => void toggleTempoReview()}>
            {isTempoReviewOpen ? "Hide Tempo Review" : "Tempo Review"}
          </button>
          {isScriptBrowserOpen ? (
            <ScriptBrowserPanel
              currentLineId={line?.id ?? null}
              lines={role.lines}
              onSelectLine={(lineId) => void jumpToLine(lineId)}
            />
          ) : null}
          {isTempoReviewOpen ? (
            <TempoReviewPanel
              attempts={reviewAttempts}
              bookmarks={bookmarks}
              role={role}
              onSelectLine={(lineId) => void jumpToLine(lineId)}
            />
          ) : null}
        </div>
      </section>
    </main>
  );
}

function ScriptBrowserPanel({
  currentLineId,
  lines,
  onSelectLine
}: {
  currentLineId: string | null;
  lines: Line[];
  onSelectLine: (lineId: string) => void;
}) {
  return (
    <div className="script-browser">
      <h2>Script</h2>
      {scriptBrowserSections(lines).map((section) => (
        <section key={section.id}>
          <h3>{section.title}</h3>
          <ol>
            {section.lines.map((line) => (
              <li key={line.id} className={line.id === currentLineId ? "current-script-line" : undefined}>
                <button type="button" className="secondary" onClick={() => onSelectLine(line.id)}>
                  <span>{line.speaker}</span>
                  {line.responseText.slice(0, 120)}
                </button>
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}

function TempoFeedbackPanel({ feedback }: { feedback: TempoFeedback }) {
  return (
    <div className="tempo-feedback">
      <p>
        Pickup: {feedback.hesitation.measuredMs} ms target {feedback.hesitation.targetMs} ms,{" "}
        {feedback.hesitation.label}.
      </p>
      {feedback.delivery ? (
        <p>
          Delivery: {feedback.delivery.measuredMs} ms target {feedback.delivery.targetMs} ms,{" "}
          {feedback.delivery.label}.
        </p>
      ) : null}
    </div>
  );
}

function TimingAttemptPanel({ attempt }: { attempt: TimingAttempt }) {
  return (
    <div className="tempo-feedback">
      <p>Last attempt:</p>
      <p>
        Pickup: {attempt.hesitationMs} ms target {attempt.targetHesitationMs} ms, {attempt.hesitationLabel}.
      </p>
      <p>
        Delivery: {attempt.deliveryMs} ms target {attempt.targetDeliveryMs} ms, {attempt.deliveryLabel}.
      </p>
    </div>
  );
}

function RecentAttemptsPanel({ attempts }: { attempts: TimingAttempt[] }) {
  return (
    <div className="tempo-feedback">
      <p>Recent attempts:</p>
      <ol className="attempt-list">
        {attempts.map((attempt) => (
          <li key={attempt.id}>
            pickup {attempt.hesitationMs} ms ({attempt.hesitationLabel}), delivery {attempt.deliveryMs} ms (
            {attempt.deliveryLabel})
          </li>
        ))}
      </ol>
    </div>
  );
}

function TempoReviewPanel({
  attempts,
  bookmarks,
  role,
  onSelectLine
}: {
  attempts: TimingAttempt[];
  bookmarks: Bookmark[];
  role: Role;
  onSelectLine: (lineId: string) => void;
}) {
  const linesById = new Map(role.lines.map((line) => [line.id, line]));
  const latePickupAttempts = attempts.filter((attempt) => attempt.hesitationLabel === "late");
  const slowDeliveryAttempts = attempts.filter((attempt) => attempt.deliveryLabel === "slow");
  const rushedDeliveryAttempts = attempts.filter((attempt) => attempt.deliveryLabel === "fast");

  return (
    <div className="tempo-review">
      <h2>Tempo Review</h2>
      <TempoReviewSection title="Late Pickup" attempts={latePickupAttempts} linesById={linesById} onSelectLine={onSelectLine} />
      <TempoReviewSection title="Slow Delivery" attempts={slowDeliveryAttempts} linesById={linesById} onSelectLine={onSelectLine} />
      <TempoReviewSection title="Rushed Delivery" attempts={rushedDeliveryAttempts} linesById={linesById} onSelectLine={onSelectLine} />
      <BookmarkReviewSection bookmarks={bookmarks} linesById={linesById} onSelectLine={onSelectLine} />
      {attempts.length === 0 && bookmarks.length === 0 ? <p className="empty">No timing attempts or bookmarks yet.</p> : null}
    </div>
  );
}

function TempoReviewSection({
  title,
  attempts,
  linesById,
  onSelectLine
}: {
  title: string;
  attempts: TimingAttempt[];
  linesById: Map<string, Line>;
  onSelectLine: (lineId: string) => void;
}) {
  return (
    <section>
      <h3>{title}</h3>
      {attempts.length === 0 ? (
        <p className="empty">None.</p>
      ) : (
        <ul>
          {attempts.map((attempt) => (
            <li key={attempt.id}>
              <button type="button" className="secondary" onClick={() => onSelectLine(attempt.lineId)}>
                {linesById.get(attempt.lineId)?.responseText.slice(0, 80) ?? attempt.lineId}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function BookmarkReviewSection({
  bookmarks,
  linesById,
  onSelectLine
}: {
  bookmarks: Bookmark[];
  linesById: Map<string, Line>;
  onSelectLine: (lineId: string) => void;
}) {
  return (
    <section>
      <h3>Bookmarked Lines</h3>
      {bookmarks.length === 0 ? (
        <p className="empty">None.</p>
      ) : (
        <ul>
          {bookmarks.map((bookmark) => (
            <li key={bookmark.id}>
              <button type="button" className="secondary" onClick={() => onSelectLine(bookmark.lineId)}>
                {linesById.get(bookmark.lineId)?.responseText.slice(0, 80) ?? bookmark.lineId}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

const minPlaybackRate = 0.4;
const maxPlaybackRate = 1.3;
const defaultPlaybackRate = 1;
const playbackRateStep = 0.1;
const playbackRates = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3];

export function clampPlaybackRate(playbackRate: number): number {
  const roundedPlaybackRate = Math.round(playbackRate * 10) / 10;
  return Math.min(maxPlaybackRate, Math.max(minPlaybackRate, roundedPlaybackRate));
}
