import type { Line } from "../../domain/line";
import type { RehearsalCommand } from "../../rehearsal/rehearsalCommand";
import {
  deliveryPillForLabel,
  formatDeliveryTimingDetails,
  formatDurationMs,
  formatPickupTimingDetails,
  pickupPillForLabel,
  type TimingStatusPill
} from "../../rehearsal/timingPresentation";
import type { PlaybackSource, PlaybackUiState } from "../hooks/useRehearsalPlayback";

type TimingPill = "delivery" | "pickup";

type RehearsalBottomBarProps = {
  playbackSource: PlaybackSource | null;
  playbackState: PlaybackUiState;
  line: Line | null;
  playbookId: string;
  lineLengthMs: number;
  latestTimingTargetDeliveryMs: number | null;
  tempoTimingEnabled: boolean;
  speakAlongEnabled: boolean;
  showLinesByDefault: boolean;
  includeBlocking: boolean;
  includeDirections: boolean;
  isCalloutEnabled: boolean;
  hasCurrentLineCallout: boolean;
  currentCueCalloutSpeaker: string | null;
  showLineInfo: boolean;
  displayedPlaybackStatus: string | TimingStatusPill | null;
  expandedTimingPill: TimingPill | null;
  absoluteTempoForgivenessMs: number;
  tempoTolerancePercent: number;
  absolutePickupForgivenessMs: number;
  onCommand: (command: RehearsalCommand) => void;
  onToggleTempoTiming: () => void;
  onToggleSpeakAlong: () => void;
  onToggleShowLinesByDefault: () => void;
  onToggleIncludeBlocking: () => void;
  onToggleIncludeDirections: () => void;
  onToggleCallout: () => void;
  onToggleLineInfo: () => void;
  onSelectRole: () => void;
  onOpenOptions: () => void;
  onToggleTimingPill: (pill: TimingPill) => void;
};

export function RehearsalBottomBar({
  playbackSource,
  playbackState,
  line,
  playbookId,
  lineLengthMs,
  latestTimingTargetDeliveryMs,
  tempoTimingEnabled,
  speakAlongEnabled,
  showLinesByDefault,
  includeBlocking,
  includeDirections,
  isCalloutEnabled,
  hasCurrentLineCallout,
  currentCueCalloutSpeaker,
  showLineInfo,
  displayedPlaybackStatus,
  expandedTimingPill,
  absoluteTempoForgivenessMs,
  tempoTolerancePercent,
  absolutePickupForgivenessMs,
  onCommand,
  onToggleTempoTiming,
  onToggleSpeakAlong,
  onToggleShowLinesByDefault,
  onToggleIncludeBlocking,
  onToggleIncludeDirections,
  onToggleCallout,
  onToggleLineInfo,
  onSelectRole,
  onOpenOptions,
  onToggleTimingPill
}: RehearsalBottomBarProps) {
  return (
    <div className="session-settings rehearsal-bottom-strip">
      <section className="control-strip line-control-strip rehearsal-bottom-line-controls" aria-label="Line controls">
        <div className="transport">
          <div className="control-group transport-group line-playback-group">
            {playbackSource === "line" && playbackState === "playing" ? (
              <button
                type="button"
                className="transport-button secondary"
                aria-label="Pause line playback. Shortcut: Space."
                title="Pause line"
                onClick={() => onCommand("pause")}
              >
                <span aria-hidden="true" className="transport-icon">
                  ⏸
                </span>
              </button>
            ) : playbackSource === "line" && playbackState === "paused" ? (
              <button
                type="button"
                className="transport-button secondary"
                aria-label="Resume line playback. Shortcut: Space."
                title="Resume line"
                onClick={() => onCommand("resume")}
              >
                <span aria-hidden="true" className="transport-icon">
                  ▶
                </span>
              </button>
            ) : (
              <button
                type="button"
                className="transport-button secondary"
                aria-label="Play your line. Shortcut: L."
                title="Play your line"
                onClick={() => onCommand("hear-line")}
                disabled={!line}
              >
                <span aria-hidden="true" className="transport-icon">
                  ▶
                </span>
              </button>
            )}
            <button
              type="button"
              className="transport-button secondary"
              aria-label="Stop line playback. Shortcut: Escape."
              title="Stop line"
              onClick={() => onCommand("stop")}
            >
              <span aria-hidden="true" className="transport-icon">
                ■
              </span>
            </button>
          </div>
        </div>
      </section>
      <div className="rehearsal-practice-toggles-inline" aria-label="Quick practice toggles">
        <button
          type="button"
          className={tempoTimingEnabled ? "quick-toggle active" : "quick-toggle"}
          aria-pressed={tempoTimingEnabled}
          aria-label={tempoTimingEnabled ? "Disable tempo timing." : "Enable tempo timing."}
          title={tempoTimingEnabled ? "Tempo timing on" : "Tempo timing off"}
          disabled={speakAlongEnabled}
          onClick={onToggleTempoTiming}
        >
          <span aria-hidden="true">⏱</span>
        </button>
        <button
          type="button"
          className={speakAlongEnabled ? "quick-toggle active" : "quick-toggle"}
          aria-pressed={speakAlongEnabled}
          aria-label={speakAlongEnabled ? "Disable speak-along practice." : "Enable speak-along practice."}
          title={speakAlongEnabled ? "Speak-along on" : "Speak-along off"}
          disabled={tempoTimingEnabled}
          onClick={onToggleSpeakAlong}
        >
          <span aria-hidden="true">👄</span>
        </button>
        <button
          type="button"
          className={showLinesByDefault ? "quick-toggle active" : "quick-toggle"}
          aria-pressed={showLinesByDefault}
          aria-label={showLinesByDefault ? "Hide lines." : "Show lines."}
          title={showLinesByDefault ? "Show lines on" : "Show lines off"}
          onClick={onToggleShowLinesByDefault}
        >
          <span aria-hidden="true">👁</span>
        </button>
        <button
          type="button"
          className={includeBlocking ? "quick-toggle active" : "quick-toggle"}
          aria-pressed={includeBlocking}
          aria-label={includeBlocking ? "Hide blocking." : "Show blocking."}
          title={includeBlocking ? "Blocking on" : "Blocking off"}
          onClick={onToggleIncludeBlocking}
        >
          <span aria-hidden="true">⌖</span>
        </button>
        <button
          type="button"
          className={includeDirections ? "quick-toggle active" : "quick-toggle"}
          aria-pressed={includeDirections}
          aria-label={includeDirections ? "Hide stage directions." : "Show stage directions."}
          title={includeDirections ? "Directions on" : "Directions off"}
          onClick={onToggleIncludeDirections}
        >
          <span aria-hidden="true">⌞⌝</span>
        </button>
        <button
          type="button"
          className={`quick-toggle${isCalloutEnabled ? " active" : ""}`}
          aria-pressed={isCalloutEnabled}
          aria-label={isCalloutEnabled ? "Disable cue callouts." : "Enable cue callouts."}
          title={
            hasCurrentLineCallout
              ? isCalloutEnabled
                ? `Callouts enabled (${currentCueCalloutSpeaker})`
                : `Callouts disabled (${currentCueCalloutSpeaker})`
              : "No callout for this cue"
          }
          onClick={onToggleCallout}
        >
          <span aria-hidden="true">📢</span>
        </button>
      </div>
      <div className="rehearsal-quick-actions">
        <button
          type="button"
          className="quick-toggle"
          aria-label={showLineInfo ? "Hide line info." : "Show line info."}
          aria-pressed={showLineInfo}
          title="Line info"
          onClick={onToggleLineInfo}
        >
          <span aria-hidden="true">ⓘ</span>
        </button>
        <button
          type="button"
          className="quick-toggle"
          aria-label="Choose role."
          title="Choose role."
          onClick={onSelectRole}
        >
          <span aria-hidden="true">🎭</span>
        </button>
        <button
          type="button"
          className="quick-toggle rehearsal-options-button"
          aria-label="Open options"
          title="Options"
          onClick={onOpenOptions}
        >
          <span aria-hidden="true">⚙</span>
        </button>
      </div>
      {displayedPlaybackStatus ? (
        <p className={typeof displayedPlaybackStatus === "string" ? "status" : "status status-timing"} aria-live="polite">
          {typeof displayedPlaybackStatus === "string" ? (
            displayedPlaybackStatus
          ) : (
            <>
              <button
                type="button"
                className={`timing-status-pill timing-status-pill--${displayedPlaybackStatus.delivery.label}`}
                aria-label={`Delivery: ${displayedPlaybackStatus.delivery.label}`}
                aria-expanded={expandedTimingPill === "delivery"}
                onClick={() => onToggleTimingPill("delivery")}
              >
                <span aria-hidden="true">{deliveryPillForLabel(displayedPlaybackStatus.delivery.label)}</span>
                <span>delivery</span>
              </button>
              <button
                type="button"
                className={`timing-status-pill timing-status-pill--${displayedPlaybackStatus.pickup.label}`}
                aria-label={`Pickup: ${displayedPlaybackStatus.pickup.label}`}
                aria-expanded={expandedTimingPill === "pickup"}
                onClick={() => onToggleTimingPill("pickup")}
              >
                <span aria-hidden="true">{pickupPillForLabel(displayedPlaybackStatus.pickup.label)}</span>
                <span>pickup</span>
              </button>
              {expandedTimingPill === "delivery" ? (
                <span className="timing-status-details">
                  {formatDeliveryTimingDetails(
                    displayedPlaybackStatus.delivery.measuredMs,
                    displayedPlaybackStatus.delivery.targetMs,
                    absoluteTempoForgivenessMs,
                    tempoTolerancePercent
                  )}
                </span>
              ) : null}
              {expandedTimingPill === "pickup" ? (
                <span className="timing-status-details">
                  {formatPickupTimingDetails(
                    displayedPlaybackStatus.pickup.measuredMs,
                    displayedPlaybackStatus.pickup.targetMs,
                    absolutePickupForgivenessMs
                  )}
                </span>
              ) : null}
            </>
          )}
        </p>
      ) : null}
      {showLineInfo && line ? (
        <div className="line-duration-panel" role="note" aria-live="polite">
          <p>Playbook: {playbookId}</p>
          <p>Line/Cue ID: {line.id}</p>
          <p>Cue file: {line.cue.audioPath}</p>
          <p>Cue length: {formatDurationMs(line.cue.durationMs)}</p>
          <p>Line length: {formatDurationMs(lineLengthMs)}</p>
          <p>Timing target: {formatDurationMs(latestTimingTargetDeliveryMs ?? lineLengthMs)}</p>
        </div>
      ) : null}
    </div>
  );
}
