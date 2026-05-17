import type { RecordingItem } from "../../domain/recordingItem";
import type { RecordingItemProgress } from "../../domain/recordingItemStatus";
import type { RecordingProjectRecord } from "../../storage/db";
import type { MicrophoneConfig } from "../microphoneConfig";
import { reasonLabel, sameContext } from "../recordingItemPresentation";
import { ContextBlock } from "./ContextBlock";
import { TakeRecorder } from "./TakeRecorder";

type ItemDetailProps = {
  project: RecordingProjectRecord;
  progress: RecordingItemProgress;
  itemNumber: number;
  itemCount: number;
  microphoneConfig: MicrophoneConfig | null;
  previousItem: RecordingItemProgress | undefined;
  nextItem: RecordingItemProgress | undefined;
  onNavigate: (item: RecordingItem) => void;
  onAccepted: () => Promise<void>;
};

export function ItemDetail({
  project,
  progress,
  itemNumber,
  itemCount,
  microphoneConfig,
  previousItem,
  nextItem,
  onNavigate,
  onAccepted
}: ItemDetailProps) {
  const { item, status } = progress;
  const showPrevious = !sameContext(item.previousSpeaker, item.previousText, item.cueSpeaker, item.cueText);
  return (
    <article className="item-detail">
      <header className="item-detail-header">
        <div className="item-heading">
          <h2>{item.id}</h2>
          <span className="line-position">line {itemNumber} of {itemCount}</span>
          <span className={status === "accepted" ? "status-pill accepted" : "status-pill"}>{status}</span>
          <span className="reason-pill">{reasonLabel(item.reason)}</span>
          <span className="line-navigation-spacer" />
          <button
            type="button"
            className="secondary icon-button"
            disabled={!previousItem}
            aria-label="Previous unaccepted line"
            title="Previous unaccepted line"
            onClick={() => previousItem && onNavigate(previousItem.item)}
          >
            &larr;
          </button>
          <button
            type="button"
            className="secondary icon-button"
            disabled={!nextItem}
            aria-label="Next unaccepted line"
            title="Next unaccepted line"
            onClick={() => nextItem && onNavigate(nextItem.item)}
          >
            &rarr;
          </button>
        </div>
      </header>

      <ContextBlock label="Cue" speaker={item.cueSpeaker} text={item.cueText} labelPosition="border" />
      {showPrevious ? <ContextBlock label="Previous" speaker={item.previousSpeaker} text={item.previousText} /> : null}

      <section className="line-panel" aria-label="Line to record">
        <div className="line-control-strip">
          <TakeRecorder
            project={project}
            item={item}
            microphoneConfig={microphoneConfig}
            onAccepted={onAccepted}
            onNavigatePrevious={previousItem ? () => onNavigate(previousItem.item) : undefined}
            onNavigateNext={nextItem ? () => onNavigate(nextItem.item) : undefined}
          />
        </div>
        <p className="line-text">{item.displayText}</p>
      </section>

      {item.stageDirections.length > 0 ? (
        <section className="stage-directions-panel">
          <p className="eyebrow">Stage Directions</p>
          <ul>
            {item.stageDirections.map((direction) => (
              <li key={direction}>{direction}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {item.blocking.length > 0 ? (
        <section className="stage-directions-panel">
          <p className="eyebrow">Blocking</p>
          <ul>
            {item.blocking.map((blocking) => (
              <li key={blocking.id}>
                <strong>{blocking.targets.join(", ")}</strong>: {blocking.text}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <ContextBlock label="Next" speaker={item.nextSpeaker} text={item.nextText} labelPosition="border" />

    </article>
  );
}
