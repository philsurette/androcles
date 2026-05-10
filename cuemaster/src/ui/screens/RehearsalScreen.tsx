import { useEffect, useState } from "react";
import type { Playbook } from "../../domain/playbook";
import type { Role } from "../../domain/role";
import type { RehearsalSession } from "../../domain/session";
import { AudioQueue } from "../../rehearsal/audioQueue";
import { RehearsalEngine } from "../../rehearsal/rehearsalEngine";
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
  const [playbackRate, setPlaybackRate] = useState(initialSession?.playbackRate ?? 1);
  const [playbackStatus, setPlaybackStatus] = useState<string>("");
  const line = engine.currentLine();
  const cues = engine.cuePayloads();

  useEffect(() => {
    void saveSession(engine.position().index);
  }, []);

  function goNext() {
    engine.next();
    updatePosition();
  }

  function goPrevious() {
    engine.previous();
    updatePosition();
  }

  function updatePosition() {
    const nextPosition = engine.position();
    setPosition(nextPosition);
    void saveSession(nextPosition.index, playbackRate);
  }

  async function saveSession(lineIndex: number, nextPlaybackRate = playbackRate) {
    await sessionRepository.save({
      playbookId: playbook.id,
      roleId: role.id,
      lineIndex,
      includeDirections: engine.includeDirections(),
      playbackRate: nextPlaybackRate,
      updatedAt: Date.now()
    });
  }

  async function playCue() {
    setPlaybackStatus("Playing cue...");
    try {
      await audioQueue.play(cues.map((cue) => ({ path: cue.audioPath, playbackRate: 1 })));
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
      await audioQueue.play(line.responseSegments.map((segment) => ({ path: segment.audioPath, playbackRate })));
      setPlaybackStatus("Line complete.");
    } catch (error) {
      setPlaybackStatus(error instanceof Error ? error.message : "Line playback failed.");
    }
  }

  function stopPlayback() {
    audioQueue.cancel();
    setPlaybackStatus("Playback stopped.");
  }

  function changePlaybackRate(nextPlaybackRate: number) {
    setPlaybackRate(nextPlaybackRate);
    void saveSession(position.index, nextPlaybackRate);
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
              <LineCard line={line} />
            </section>
          </div>
        ) : (
          <p className="empty">This role has no rehearsable lines.</p>
        )}

        <div className="transport">
          <button type="button" className="secondary" disabled={position.atBeginning} onClick={goPrevious}>
            Previous
          </button>
          <button type="button" onClick={() => void playCue()}>
            Repeat Cue
          </button>
          <button type="button" onClick={() => void playResponse()} disabled={!line}>
            Hear My Line
          </button>
          <button type="button" disabled={position.atEnd} onClick={goNext}>
            Next
          </button>
          <button type="button" className="secondary" onClick={stopPlayback}>
            Stop
          </button>
        </div>

        <div className="session-settings">
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
          {playbackStatus ? <p className="status">{playbackStatus}</p> : null}
        </div>
      </section>
    </main>
  );
}

const playbackRates = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.2, 1.3];
