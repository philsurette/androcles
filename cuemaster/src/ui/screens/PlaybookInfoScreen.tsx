import type { Playbook } from "../../domain/playbook";

type PlaybookInfoScreenProps = {
  playbook: Playbook;
  onBack: () => void;
};

export function PlaybookInfoScreen({ playbook, onBack }: PlaybookInfoScreenProps) {
  const totalLines = playbook.roles.reduce((sum, role) => sum + role.lines.length, 0);

  return (
    <main className="shell">
      <section className="hero playbook-info">
        <header className="rehearsal-header">
          <div className="breadcrumb-row">
            <button
              type="button"
              className="icon-button secondary"
              aria-label={`Back to library`}
              title="Back to library"
              onClick={onBack}
            >
              <span aria-hidden="true">←</span>
            </button>
            <div className="rehearsal-title-stack">
              <p className="rehearsal-play-title">{playbook.title}</p>
              <p className="playbook-info-subtitle">Playbook information</p>
            </div>
          </div>
        </header>

        <dl className="playbook-metadata-list">
          <div>
            <dt>Title</dt>
            <dd>{playbook.title}</dd>
          </div>
          <div>
            <dt>Play ID</dt>
            <dd>{playbook.id}</dd>
          </div>
          <div>
            <dt>Authors</dt>
            <dd>{playbook.authors.join(", ") || "Unknown"}</dd>
          </div>
          <div>
            <dt>Roles</dt>
            <dd>{playbook.roles.length}</dd>
          </div>
          <div>
            <dt>Lines</dt>
            <dd>{totalLines}</dd>
          </div>
          {playbook.source ? (
            <div>
              <dt>Source</dt>
              <dd>{playbook.source}</dd>
            </div>
          ) : null}
          <div>
            <dt>Build ID</dt>
            <dd>{playbook.build?.buildId ?? "Unknown"}</dd>
          </div>
          <div>
            <dt>Build timestamp</dt>
            <dd>{playbook.build?.buildTimestamp ?? "Unknown"}</dd>
          </div>
          <div>
            <dt>Sections</dt>
            <dd>{playbook.sections.length}</dd>
          </div>
          <div>
            <dt>Context items</dt>
            <dd>{playbook.context.length}</dd>
          </div>
        </dl>
      </section>
    </main>
  );
}
