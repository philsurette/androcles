import type { Cue } from "../../domain/cue";
import type { Line } from "../../domain/line";
import type { RehearsalCommand } from "../../rehearsal/rehearsalCommand";
import { visibleBlockingForLine } from "../../rehearsal/rehearsalPresentation";
import type { PlaybackSource, PlaybackUiState } from "../hooks/useRehearsalPlayback";
import { CueCard } from "./CueCard";
import { LineCard, type BlockingScope } from "./LineCard";

type RehearsalLineWorkspaceProps = {
  line: Line | null;
  roleDisplayName: string;
  rehearsalTextSize: string;
  visibleCues: Cue[];
  playbackSource: PlaybackSource | null;
  playbackState: PlaybackUiState;
  hasStarted: boolean;
  atBeginning: boolean;
  atEnd: boolean;
  bookmarkNeighbors: {
    previousLineId: string | null;
    nextLineId: string | null;
  };
  isCurrentLineBookmarked: boolean;
  includeBlocking: boolean;
  includeDirections: boolean;
  isLineRevealed: boolean;
  blockingScope: BlockingScope;
  onCommand: (command: RehearsalCommand) => void;
  onJumpToLine: (lineId: string) => void;
};

export function RehearsalLineWorkspace({
  line,
  roleDisplayName,
  rehearsalTextSize,
  visibleCues,
  playbackSource,
  playbackState,
  hasStarted,
  atBeginning,
  atEnd,
  bookmarkNeighbors,
  isCurrentLineBookmarked,
  includeBlocking,
  includeDirections,
  isLineRevealed,
  blockingScope,
  onCommand,
  onJumpToLine
}: RehearsalLineWorkspaceProps) {
  if (!line) {
    return <p className="empty">This role has no rehearsable lines.</p>;
  }

  return (
    <div className={`rehearsal-line-layout rehearsal-text-size rehearsal-text-size-${rehearsalTextSize}`}>
      <fieldset className="cue-section-panel" aria-label={`Cue: ${visibleCues[0]?.speaker ?? roleDisplayName}`}>
        <legend className="cue-section-title">{`Cue: ${visibleCues[0]?.speaker ?? roleDisplayName}`}</legend>
        <section className="cue-strip" aria-label="Cue">
          <section className="control-strip cue-control-strip" aria-label="Cue controls">
            <div className="transport">
              <div className="control-group transport-group cue-play-group">
                {playbackSource === "cue" && playbackState === "playing" ? (
                  <button
                    type="button"
                    className="transport-button secondary"
                    aria-label="Pause cue playback. Shortcut: Space."
                    title="Pause cue"
                    onClick={() => onCommand("pause")}
                  >
                    <span aria-hidden="true" className="transport-icon">
                      ⏸
                    </span>
                  </button>
                ) : null}
                {playbackSource === "cue" && playbackState === "paused" ? (
                  <button
                    type="button"
                    className="transport-button secondary"
                    aria-label="Resume cue playback. Shortcut: Space."
                    title="Resume cue"
                    onClick={() => onCommand("resume")}
                  >
                    <span aria-hidden="true" className="transport-icon">
                      ▶
                    </span>
                  </button>
                ) : null}
                {playbackSource !== "cue" || playbackState === "idle" ? (
                  <button
                    type="button"
                    className="transport-button secondary"
                    aria-label={`${hasStarted ? "Replay cue" : "Play cue"}. Shortcut: R.`}
                    title={hasStarted ? "Replay cue" : "Play cue"}
                    onClick={() => onCommand("repeat-cue")}
                  >
                    <span aria-hidden="true" className="transport-icon">
                      ▶
                    </span>
                  </button>
                ) : null}
                <button
                  type="button"
                  className="transport-button secondary"
                  aria-label="Stop cue playback. Shortcut: Escape."
                  title="Stop"
                  onClick={() => onCommand("stop")}
                >
                  <span aria-hidden="true" className="transport-icon">
                    ■
                  </span>
                </button>
              </div>
              <div className="control-group transport-group cue-navigation-group">
                <button
                  type="button"
                  className="transport-button secondary"
                  aria-label="Go to previous line. Shortcut: Left arrow."
                  title="Previous line"
                  disabled={atBeginning}
                  onClick={() => onCommand("back")}
                >
                  <span aria-hidden="true" className="transport-icon">
                    ⏮
                  </span>
                </button>
                <button
                  type="button"
                  className="transport-button secondary"
                  aria-label="Go to next line. Shortcut: Right arrow."
                  title="Next line"
                  disabled={atEnd}
                  onClick={() => onCommand("next")}
                >
                  <span aria-hidden="true" className="transport-icon">
                    ⏭
                  </span>
                </button>
              </div>
              <div className="control-group transport-group cue-bookmark-group">
                <button
                  type="button"
                  className="quick-toggle"
                  aria-label="Go to previous bookmark."
                  title="Previous bookmark"
                  onClick={() => bookmarkNeighbors.previousLineId && onJumpToLine(bookmarkNeighbors.previousLineId)}
                  disabled={!bookmarkNeighbors.previousLineId}
                >
                  <span aria-hidden="true">↤</span>
                </button>
                <button
                  type="button"
                  className={isCurrentLineBookmarked ? "quick-toggle active" : "quick-toggle"}
                  aria-pressed={isCurrentLineBookmarked}
                  aria-label={
                    isCurrentLineBookmarked
                      ? "Remove bookmark from current line."
                      : "Bookmark current line."
                  }
                  title={isCurrentLineBookmarked ? "Bookmarked" : "Bookmark"}
                  onClick={() => onCommand("bookmark")}
                >
                  <span aria-hidden="true">{isCurrentLineBookmarked ? "★" : "☆"}</span>
                </button>
                <button
                  type="button"
                  className="quick-toggle"
                  aria-label="Go to next bookmark."
                  title="Next bookmark"
                  onClick={() => bookmarkNeighbors.nextLineId && onJumpToLine(bookmarkNeighbors.nextLineId)}
                  disabled={!bookmarkNeighbors.nextLineId}
                >
                  <span aria-hidden="true">↦</span>
                </button>
              </div>
            </div>
          </section>
          <div className="cue-strip-cards">
            {visibleCues.map((cue, index) => (
              <CueCard cue={cue} showSpeaker={false} key={`${line.id}-cue-${index}`} />
            ))}
            {includeBlocking
              ? visibleBlockingForLine(line, blockingScope)
                  .filter((blocking) => blocking.placement !== "inline")
                  .map((blocking) => (
                    <article
                      className="card cue-card cue-blocking-card"
                      key={`${blocking.id}-${blocking.segmentId ?? "context"}-${blocking.placement}`}
                    >
                      <p className="speaker blocking-target">{blocking.targets.join(", ")}</p>
                      <p className="cue-blocking-text">({blocking.text})</p>
                    </article>
                  ))
              : null}
          </div>
        </section>
      </fieldset>

      <section className="stack" aria-label="Current cue and line">
        <div className="rehearsal-line-content">
          {isLineRevealed ? (
            <LineCard
              line={line}
              includeDirections={includeDirections}
              includeBlocking={includeBlocking}
              blockingScope={blockingScope}
            />
          ) : (
            <article className="card hidden-line">Line hidden</article>
          )}
        </div>
      </section>
    </div>
  );
}
