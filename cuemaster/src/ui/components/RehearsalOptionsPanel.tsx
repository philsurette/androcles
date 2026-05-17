import { cueWindowPresets } from "../../rehearsal/cueWindowPreset";
import {
  absolutePickupForgivenessOptionsMs,
  absoluteTempoForgivenessOptionsMs,
  formatAbsoluteTempoForgiveness,
  formatTempoEndOfLineSilence,
  formatTempoTolerancePercent,
  formatTimingOption,
  playbackRates,
  practicePaceMultiplierOptions,
  practiceTimingOptionsMs,
  rehearsalTextSizeOptions,
  tempoEndOfLineSilenceOptionsMs,
  tempoToleranceOptionsPercent,
  type RehearsalTextSize
} from "../../rehearsal/timingPresentation";
import type { AutoAdvanceMode, AutoPlayLineMode } from "../hooks/useRehearsalSettings";
import type { BlockingScope } from "./LineCard";
import { PracticeSelect } from "./PracticeSelect";

type RehearsalOptionsPanelProps = {
  cueWindowPresetId: string;
  blockingScope: BlockingScope;
  rehearsalTextSize: RehearsalTextSize;
  playbackRate: number;
  practiceTargetPaceMultiplier: number;
  syncSpeakAlongSpeed: boolean;
  absoluteTempoForgivenessMs: number;
  tempoTolerancePercent: number;
  speakAlongPauseMs: number;
  tempoTargetHesitationMs: number;
  syncPracticeTiming: boolean;
  absolutePickupForgivenessMs: number;
  tempoEndOfLineSilenceMs: number;
  autoAdvanceMode: AutoAdvanceMode;
  autoPlayLineMode: AutoPlayLineMode;
  onCueWindowPresetChange: (value: string) => void;
  onBlockingScopeChange: (value: BlockingScope) => void;
  onRehearsalTextSizeChange: (value: RehearsalTextSize) => void;
  onPlaybackRateChange: (value: number) => void;
  onPracticeTargetPaceMultiplierChange: (value: number) => void;
  onSyncSpeakAlongSpeedChange: (value: boolean) => void;
  onAbsoluteTempoForgivenessChange: (value: number) => void;
  onTempoTolerancePercentChange: (value: number) => void;
  onSpeakAlongPauseMsChange: (value: number) => void;
  onTempoTargetHesitationMsChange: (value: number) => void;
  onSyncPracticeTimingChange: (value: boolean) => void;
  onAbsolutePickupForgivenessChange: (value: number) => void;
  onTempoEndOfLineSilenceMsChange: (value: number) => void;
  onAutoAdvanceModeChange: (value: AutoAdvanceMode) => void;
  onAutoPlayLineModeChange: (value: AutoPlayLineMode) => void;
};

export function RehearsalOptionsPanel({
  cueWindowPresetId,
  blockingScope,
  rehearsalTextSize,
  playbackRate,
  practiceTargetPaceMultiplier,
  syncSpeakAlongSpeed,
  absoluteTempoForgivenessMs,
  tempoTolerancePercent,
  speakAlongPauseMs,
  tempoTargetHesitationMs,
  syncPracticeTiming,
  absolutePickupForgivenessMs,
  tempoEndOfLineSilenceMs,
  autoAdvanceMode,
  autoPlayLineMode,
  onCueWindowPresetChange,
  onBlockingScopeChange,
  onRehearsalTextSizeChange,
  onPlaybackRateChange,
  onPracticeTargetPaceMultiplierChange,
  onSyncSpeakAlongSpeedChange,
  onAbsoluteTempoForgivenessChange,
  onTempoTolerancePercentChange,
  onSpeakAlongPauseMsChange,
  onTempoTargetHesitationMsChange,
  onSyncPracticeTimingChange,
  onAbsolutePickupForgivenessChange,
  onTempoEndOfLineSilenceMsChange,
  onAutoAdvanceModeChange,
  onAutoPlayLineModeChange
}: RehearsalOptionsPanelProps) {
  return (
    <div className="practice-options-page">
      <div className="practice-options-panel">
        <div className="practice-options-inline-row">
          <label className="timing-setting timing-setting-inline timing-setting-inline-wide">
            Cue length
            <PracticeSelect
              label="Cue length"
              value={cueWindowPresetId}
              options={cueWindowPresets.map((preset) => ({ value: preset.id, label: preset.label }))}
              onSelect={onCueWindowPresetChange}
            />
          </label>
          <label className="timing-setting timing-setting-inline timing-setting-inline-wide">
            Blocking scope
            <PracticeSelect
              label="Blocking scope"
              value={blockingScope}
              options={[
                { value: "role", label: "My role" },
                { value: "all", label: "All roles" }
              ]}
              onSelect={(next) => onBlockingScopeChange(next as BlockingScope)}
            />
          </label>
          <label className="timing-setting timing-setting-inline timing-setting-inline-wide">
            Text size
            <PracticeSelect
              label="Text size"
              value={rehearsalTextSize}
              options={rehearsalTextSizeOptions.map((option) => ({
                value: option,
                label: option
              }))}
              onSelect={(next) => onRehearsalTextSizeChange(next as RehearsalTextSize)}
            />
          </label>
        </div>
        <details className="timing-options timing-options-collapsible">
          <summary className="timing-options-summary">Tempo</summary>
          <div className="timing-options-controls">
            <div className="timing-targets-row">
              <div className="timing-targets-controls">
                <label className="timing-setting">
                  Speakalong
                  <PracticeSelect
                    label="Speakalong"
                    value={String(playbackRate)}
                    options={playbackRates.map((rate) => ({ value: String(rate), label: `${rate.toFixed(1)}x` }))}
                    onSelect={(next) => onPlaybackRateChange(Number(next))}
                  />
                </label>
                <label className="timing-setting">
                  Target adj.
                  <PracticeSelect
                    label="Target adj."
                    value={String(practiceTargetPaceMultiplier)}
                    options={practicePaceMultiplierOptions.map((optionMultiplier) => ({
                      value: String(optionMultiplier),
                      label: `${optionMultiplier.toFixed(1)}x`
                    }))}
                    onSelect={(next) => onPracticeTargetPaceMultiplierChange(Number(next))}
                    disabled={syncSpeakAlongSpeed}
                  />
                </label>
              </div>
              <button
                type="button"
                className={`timing-sync-toggle ${syncSpeakAlongSpeed ? "linked" : ""}`}
                aria-label={syncSpeakAlongSpeed ? "Disable speed control sync." : "Keep speed controls in sync."}
                aria-pressed={syncSpeakAlongSpeed}
                title={syncSpeakAlongSpeed ? "Unlock speed controls" : "Lock speed controls"}
                onClick={() => onSyncSpeakAlongSpeedChange(!syncSpeakAlongSpeed)}
              >
                <span aria-hidden="true">{syncSpeakAlongSpeed ? "🔒" : "🔓"}</span>
              </button>
            </div>
            <label className="timing-setting">
              Forgiveness(abs)
              <PracticeSelect
                label="Forgiveness(abs)"
                value={String(absoluteTempoForgivenessMs)}
                options={absoluteTempoForgivenessOptionsMs.map((optionMs) => ({
                  value: String(optionMs),
                  label: formatAbsoluteTempoForgiveness(optionMs)
                }))}
                onSelect={(next) => onAbsoluteTempoForgivenessChange(Number(next))}
              />
            </label>
            <label className="timing-setting">
              Forgiveness(%)
              <PracticeSelect
                label="Forgiveness(%)"
                value={String(tempoTolerancePercent)}
                options={tempoToleranceOptionsPercent.map((optionPercent) => ({
                  value: String(optionPercent),
                  label: formatTempoTolerancePercent(optionPercent)
                }))}
                onSelect={(next) => onTempoTolerancePercentChange(Number(next))}
              />
            </label>
          </div>
        </details>
        <details className="timing-options timing-options-collapsible">
          <summary className="timing-options-summary">Cue Pickup</summary>
          <div className="timing-options-controls">
            <div className="timing-targets-row">
              <div className="timing-targets-controls">
                <label className="timing-setting">
                  Speaking pause
                  <PracticeSelect
                    label="Speaking pause"
                    value={String(speakAlongPauseMs)}
                    options={practiceTimingOptionsMs.map((optionMs) => ({
                      value: String(optionMs),
                      label: formatTimingOption(optionMs)
                    }))}
                    onSelect={(next) => onSpeakAlongPauseMsChange(Number(next))}
                  />
                </label>
                <label className="timing-setting">
                  Pickup target
                  <PracticeSelect
                    label="Pickup target"
                    value={String(tempoTargetHesitationMs)}
                    options={practiceTimingOptionsMs.map((optionMs) => ({
                      value: String(optionMs),
                      label: formatTimingOption(optionMs)
                    }))}
                    onSelect={(next) => onTempoTargetHesitationMsChange(Number(next))}
                    disabled={syncPracticeTiming}
                  />
                </label>
              </div>
              <button
                type="button"
                className={`timing-sync-toggle ${syncPracticeTiming ? "linked" : ""}`}
                aria-label={syncPracticeTiming ? "Disable sync for timing targets." : "Keep timing targets in sync."}
                aria-pressed={syncPracticeTiming}
                title={syncPracticeTiming ? "Unlock timing targets" : "Lock timing targets"}
                onClick={() => onSyncPracticeTimingChange(!syncPracticeTiming)}
              >
                <span aria-hidden="true">{syncPracticeTiming ? "🔒" : "🔓"}</span>
              </button>
            </div>
            <label className="timing-setting">
              Forgiveness
              <PracticeSelect
                label="Forgiveness"
                value={String(absolutePickupForgivenessMs)}
                options={absolutePickupForgivenessOptionsMs.map((optionMs) => ({
                  value: String(optionMs),
                  label: formatAbsoluteTempoForgiveness(optionMs)
                }))}
                onSelect={(next) => onAbsolutePickupForgivenessChange(Number(next))}
              />
            </label>
            <label className="timing-setting">
              Line silence
              <PracticeSelect
                label="Line silence"
                value={String(tempoEndOfLineSilenceMs)}
                options={tempoEndOfLineSilenceOptionsMs.map((optionMs) => ({
                  value: String(optionMs),
                  label: formatTempoEndOfLineSilence(optionMs)
                }))}
                onSelect={(next) => onTempoEndOfLineSilenceMsChange(Number(next))}
              />
            </label>
          </div>
        </details>
        <details className="timing-options timing-options-collapsible">
          <summary className="timing-options-summary">Autoadvance</summary>
          <div className="timing-options-controls">
            <label className="timing-setting timing-setting-2x">
              Advance
              <PracticeSelect
                label="Advance"
                value={autoAdvanceMode}
                options={[
                  { value: "disabled", label: "Disabled" },
                  { value: "always", label: "Always" },
                  { value: "on-target", label: "When on target" },
                  { value: "when-not-slow", label: "When not slow" }
                ]}
                onSelect={(next) => onAutoAdvanceModeChange(next as AutoAdvanceMode)}
              />
            </label>
            <label className="timing-setting timing-setting-2x">
              Replay line
              <PracticeSelect
                label="Replay line"
                value={autoPlayLineMode}
                options={[
                  { value: "disabled", label: "Disabled" },
                  { value: "always", label: "Always" },
                  { value: "off-target", label: "When off target" }
                ]}
                onSelect={(next) => onAutoPlayLineModeChange(next as AutoPlayLineMode)}
                disabled={autoAdvanceMode === "disabled"}
              />
            </label>
          </div>
        </details>
      </div>
    </div>
  );
}
