import { useEffect, useState } from "react";
import type { Playbook } from "../../domain/playbook";
import type { Role } from "../../domain/role";
import type { RehearsalSession } from "../../domain/session";
import { AudioQueue } from "../../rehearsal/audioQueue";
import { cuePlaybackItems, responsePlaybackItems, speakAlongPlaybackItems } from "../../rehearsal/playbackItems";
import { RehearsalEngine } from "../../rehearsal/rehearsalEngine";
import { VoiceActivityDetector } from "../../rehearsal/voiceActivityDetector";
import { sessionRepository } from "../../storage/sessionRepository";
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
  const [tempoTimingEnabled, setTempoTimingEnabled] = useState(initialSession?.tempoTimingEnabled ?? false);
  const [tempoStatus, setTempoStatus] = useState<string>("");
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

  async function goNext() {
    engine.next();
    updatePosition();
    setIsLineRevealed(false);
    if (hasStarted) {
      await playCue();
    }
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
    void saveSession(nextPosition.index, playbackRate);
  }

  async function saveSession(
    lineIndex: number,
    nextPlaybackRate = playbackRate,
    nextSpeakAlongEnabled = speakAlongEnabled,
    nextTempoTimingEnabled = tempoTimingEnabled
  ) {
    await sessionRepository.save({
      playbookId: playbook.id,
      roleId: role.id,
      lineIndex,
      includeDirections: engine.includeDirections(),
      playbackRate: nextPlaybackRate,
      speakAlongEnabled: nextSpeakAlongEnabled,
      tempoTimingEnabled: nextTempoTimingEnabled,
      updatedAt: Date.now()
    });
  }

  async function playCue() {
    setHasStarted(true);
    setPlaybackStatus("Playing cue...");
    try {
      await audioQueue.play(cuePlaybackItems(cues));
      setPlaybackStatus("Cue complete.");
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
    void saveSession(position.index, playbackRate, nextSpeakAlongEnabled, nextSpeakAlongEnabled ? false : tempoTimingEnabled);
  }

  async function enableTempoTiming() {
    setTempoStatus("Requesting microphone permission...");
    const detector = new VoiceActivityDetector((result) => {
      if (result.event === "speech-started") {
        setTempoStatus(`Speech detected after ${result.hesitationMs} ms.`);
      } else {
        setTempoStatus(`Delivery ended after ${result.deliveryMs} ms.`);
      }
    });

    try {
      await detector.start();
      voiceActivityDetector?.stop();
      setVoiceActivityDetector(detector);
      setTempoTimingEnabled(true);
      setSpeakAlongEnabled(false);
      setTempoStatus("Tempo timing enabled. Audio is not recorded, transcribed, saved, or uploaded.");
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
    setTempoStatus(message);
    await saveSession(position.index, playbackRate, speakAlongEnabled, false);
  }

  return (
    <main className="shell">
      <section className="hero rehearsal">
        <button type="button" className="secondary" onClick={onBack}>
          Back to Roles
        </button>
        <p className="eyebrow">{role.displayName}</p>
        <h1>{playbook.title}</h1>
        <p>
          Line {position.total === 0 ? 0 : position.index + 1} of {position.total}
        </p>

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
          <button type="button" onClick={() => void playCue()}>
            {hasStarted ? "Repeat Cue" : "Start"}
          </button>
          <button type="button" className="secondary" disabled={position.atBeginning} onClick={() => void goPrevious()}>
            Previous
          </button>
          <button type="button" className="secondary" disabled={!line} onClick={() => setIsLineRevealed(!isLineRevealed)}>
            {isLineRevealed ? "Hide Line" : "Reveal Line"}
          </button>
          <button type="button" onClick={() => void playResponse()} disabled={!line}>
            Hear My Line
          </button>
          <button type="button" onClick={() => void speakAlong()} disabled={!line}>
            Speak Along
          </button>
          <button type="button" disabled={position.atEnd} onClick={() => void goNext()}>
            Next
          </button>
          <button type="button" className="secondary" onClick={stopPlayback}>
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
          {playbackStatus ? <p className="status">{playbackStatus}</p> : null}
        </div>
      </section>
    </main>
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
