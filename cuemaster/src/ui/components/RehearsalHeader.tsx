type RehearsalHeaderProps = {
  playTitle: string;
  roleTitle: string;
  backLabel: string;
  backTitle: string;
  onBack: () => void;
  lineId?: string | null;
  isOutlineOpen?: boolean;
  onOpenOutline?: () => void;
};

export function RehearsalHeader({
  playTitle,
  roleTitle,
  backLabel,
  backTitle,
  onBack,
  lineId,
  isOutlineOpen = false,
  onOpenOutline
}: RehearsalHeaderProps) {
  return (
    <header className="rehearsal-header">
      <div className="breadcrumb-row">
        <button
          type="button"
          className="icon-button secondary"
          aria-label={backLabel}
          title={backTitle}
          onClick={onBack}
        >
          <span aria-hidden="true">←</span>
        </button>
        <div className="rehearsal-title-stack">
          <p className="rehearsal-play-title">{playTitle}</p>
          <p className="rehearsal-role-title">{roleTitle}</p>
        </div>
      </div>
      {lineId !== undefined ? (
        <div className="rehearsal-line-metadata">
          <button
            type="button"
            className="outline-open-button icon-button secondary"
            aria-label={isOutlineOpen ? "Browse cues" : "Open cues"}
            title={isOutlineOpen ? "Browse cues" : "Open cues"}
            onClick={onOpenOutline}
          >
            <span aria-hidden="true">📋</span>
          </button>
          <p className="line-position">{lineId ?? "No lines"}</p>
        </div>
      ) : null}
    </header>
  );
}
