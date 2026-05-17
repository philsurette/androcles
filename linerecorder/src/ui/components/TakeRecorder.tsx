import { meterFillPercentForLevel } from "../../audio/inputMeter";
import type { RecordingItem } from "../../domain/recordingItem";
import type { RecordingProjectRecord } from "../../storage/db";
import { useTakeRecorder } from "../hooks/useTakeRecorder";
import type { MicrophoneConfig } from "../microphoneConfig";
import { levelLabel } from "../recordingItemPresentation";

type TakeRecorderProps = {
  project: RecordingProjectRecord;
  item: RecordingItem;
  microphoneConfig: MicrophoneConfig | null;
  onAccepted: () => Promise<void>;
  onNavigatePrevious?: () => void;
  onNavigateNext?: () => void;
};

export function TakeRecorder({
  project,
  item,
  microphoneConfig,
  onAccepted,
  onNavigatePrevious,
  onNavigateNext
}: TakeRecorderProps) {
  const {
    isRecording,
    currentTake,
    acceptedTake,
    recordingReading,
    playingSource,
    status,
    statusTone,
    startRecording,
    stopRecording,
    playTake,
    playAcceptedTake,
    acceptTake,
    discardTake,
    stopPlayback
  } = useTakeRecorder({ project, item, microphoneConfig, onAccepted });

  return (
    <section className="take-panel" aria-label="Take recorder">
      {isRecording ? (
        <div className="take-controls recording-active">
          <button type="button" className="record-control stop-control" aria-label="Stop recording" title="Stop recording" onClick={stopRecording}>
            <span aria-hidden="true">■</span>
          </button>
          <div className="meter-row take-meter">
            <div className="meter" aria-label={`Recording input level: ${levelLabel(recordingReading.level)}`}>
              <span style={{ width: `${meterFillPercentForLevel(recordingReading.energy, recordingReading.level)}%` }} />
            </div>
            <span className={`meter-label ${recordingReading.level}`}>{levelLabel(recordingReading.level)}</span>
          </div>
        </div>
      ) : (
        <div className="take-controls">
          <div className="take-control-group">
            <button
              type="button"
              className="record-control"
              aria-label={currentTake ? "Record another take" : acceptedTake ? "Record replacement take" : "Record"}
              title={currentTake ? "Record another take" : acceptedTake ? "Record replacement take" : "Record"}
              onClick={() => void startRecording()}
            >
              <span aria-hidden="true">●</span>
            </button>
            {playingSource === "take" || playingSource === "saved" ? (
              <button type="button" className="secondary recorder-icon-button" aria-label="Stop playback" title="Stop playback" onClick={stopPlayback}>
                <span aria-hidden="true">■</span>
              </button>
            ) : (
              <button
                type="button"
                className="secondary recorder-icon-button"
                disabled={!currentTake && !acceptedTake}
                aria-label="Play take"
                title="Play take"
                onClick={() => (currentTake ? playTake() : playAcceptedTake())}
              >
                <span aria-hidden="true">▶</span>
              </button>
            )}
            <button
              type="button"
              className="secondary recorder-icon-button accept-control"
              disabled={!currentTake || isRecording}
              aria-label="Accept take"
              title="Accept take"
              onClick={() => void acceptTake()}
            >
              <span aria-hidden="true">✓</span>
            </button>
            {currentTake ? (
              <button
                type="button"
                className="secondary recorder-icon-button discard-control"
                disabled={isRecording}
                aria-label="Discard current take"
                title="Discard current take"
                onClick={discardTake}
              >
                <span aria-hidden="true">×</span>
              </button>
            ) : null}
          </div>
          <div className="take-control-group">
            <button
              type="button"
              className="secondary recorder-icon-button"
              disabled={!onNavigatePrevious}
              aria-label="Previous unaccepted line"
              title="Previous unaccepted line"
              onClick={() => onNavigatePrevious?.()}
            >
              <span aria-hidden="true">◁</span>
            </button>
            <button
              type="button"
              className="secondary recorder-icon-button"
              disabled={!onNavigateNext}
              aria-label="Next unaccepted line"
              title="Next unaccepted line"
              onClick={() => onNavigateNext?.()}
            >
              <span aria-hidden="true">▷</span>
            </button>
          </div>
        </div>
      )}
      <div className="take-status-row">
        <p className={statusTone === "warning" ? "take-status warning" : "take-status"}>{status}</p>
      </div>
    </section>
  );
}
