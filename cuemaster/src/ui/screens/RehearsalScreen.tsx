import { useState } from "react";
import type { Playbook } from "../../domain/playbook";
import type { Role } from "../../domain/role";
import { RehearsalEngine } from "../../rehearsal/rehearsalEngine";
import { CueCard } from "../components/CueCard";
import { LineCard } from "../components/LineCard";

type RehearsalScreenProps = {
  playbook: Playbook;
  role: Role;
  onBack: () => void;
};

export function RehearsalScreen({ playbook, role, onBack }: RehearsalScreenProps) {
  const [engine] = useState(() => RehearsalEngine.forRole(playbook, role.id));
  const [position, setPosition] = useState(() => engine.position());
  const line = engine.currentLine();
  const cues = engine.cuePayloads();

  function goNext() {
    engine.next();
    setPosition(engine.position());
  }

  function goPrevious() {
    engine.previous();
    setPosition(engine.position());
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
          <button type="button" disabled={position.atEnd} onClick={goNext}>
            Next
          </button>
        </div>
      </section>
    </main>
  );
}
