import type { ComponentProps } from "react";
import { RehearsalHeader } from "./RehearsalHeader";
import { RehearsalOptionsPanel } from "./RehearsalOptionsPanel";

type RehearsalOptionsScreenProps = {
  playTitle: string;
  storageStatus: string;
  onBackToRehearsal: () => void;
  options: ComponentProps<typeof RehearsalOptionsPanel>;
};

export function RehearsalOptionsScreen({
  playTitle,
  storageStatus,
  onBackToRehearsal,
  options
}: RehearsalOptionsScreenProps) {
  return (
    <main className="shell">
      <section className="hero rehearsal">
        <RehearsalHeader
          playTitle={playTitle}
          roleTitle="Rehearse options"
          backLabel="Back to rehearsal."
          backTitle="Back to rehearsal"
          onBack={onBackToRehearsal}
        />
        {storageStatus ? (
          <p className="error" role="alert">
            {storageStatus}
          </p>
        ) : null}
        <div className="rehearsal-workspace no-outline options-workspace options-workspace-shell">
          <div className="practice-options-scroll">
            <RehearsalOptionsPanel {...options} />
          </div>
        </div>
      </section>
    </main>
  );
}
