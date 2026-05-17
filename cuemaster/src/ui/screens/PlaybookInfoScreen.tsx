import type { Playbook } from "../../domain/playbook";

type PlaybookInfoScreenProps = {
  playbook: Playbook;
  onBack: () => void;
};

function formatLocalBuildTime(timestamp: string | undefined): string {
  if (timestamp === undefined) {
    return "Unknown";
  }
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return `${timestamp} (invalid timestamp)`;
  }

  const local = new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZoneName: "short",
  }).format(date);

  return `${timestamp} (${local})`;
}

export function PlaybookInfoScreen({ playbook, onBack }: PlaybookInfoScreenProps) {
  const totalLines = playbook.roles.reduce((sum, role) => sum + role.lines.length, 0);
  const manifestText = playbook.manifestText ?? JSON.stringify({
    id: playbook.id,
    title: playbook.title,
    authors: playbook.authors,
    build: playbook.build,
    production: playbook.production,
    sections: playbook.sections,
    context: playbook.context,
    roles: playbook.roles,
    source: playbook.source,
    schemaVersion: playbook.schemaVersion,
  }, null, 2);

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
            <dd>{formatLocalBuildTime(playbook.build?.buildTimestamp)}</dd>
          </div>
          <div>
            <dt>Production source</dt>
            <dd>{playbook.production.source}</dd>
          </div>
          <div>
            <dt>Production version</dt>
            <dd>{playbook.production.version ?? "Unpublished"}</dd>
          </div>
          {playbook.production.publishedAt ? (
            <div>
              <dt>Production published</dt>
              <dd>{formatLocalBuildTime(playbook.production.publishedAt)}</dd>
            </div>
          ) : null}
          <div>
            <dt>Sections</dt>
            <dd>{playbook.sections.length}</dd>
          </div>
          <div>
            <dt>Context items</dt>
            <dd>{playbook.context.length}</dd>
          </div>
        </dl>

        <details className="playbook-manifest-details">
          <summary>Manifest</summary>
          <pre>{manifestText}</pre>
        </details>
      </section>
    </main>
  );
}
