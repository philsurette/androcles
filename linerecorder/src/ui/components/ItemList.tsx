import { useLayoutEffect, useRef, useState } from "react";
import type { RecordingItem } from "../../domain/recordingItem";
import type { RecordingItemProgress } from "../../domain/recordingItemStatus";
import { recordingItemSearchText } from "../recordingItemPresentation";

type ItemListProps = {
  progress: RecordingItemProgress[];
  selectedItemId: string | undefined;
  isOpen: boolean;
  onToggleOpen: () => void;
  onSelectItem: (item: RecordingItem) => void;
};

export function ItemList({ progress, selectedItemId, isOpen, onToggleOpen, onSelectItem }: ItemListProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const acceptedCount = progress.filter((candidate) => candidate.status === "accepted").length;
  const selectedRowRef = useRef<HTMLButtonElement | null>(null);
  const normalizedSearchQuery = searchQuery.trim().toLocaleLowerCase();
  const filteredProgress = progress.filter(({ item }) =>
    recordingItemSearchText(item).toLocaleLowerCase().includes(normalizedSearchQuery)
  );

  useLayoutEffect(() => {
    if (isOpen) {
      selectedRowRef.current?.scrollIntoView({ block: "nearest" });
    }
  }, [isOpen, selectedItemId]);

  if (!isOpen) {
    return null;
  }

  return (
    <aside className="item-explorer" aria-label="Recording items">
      <div className="item-explorer-header">
        <div>
          <p className="eyebrow">Lines</p>
          <strong>{acceptedCount}/{progress.length} requested recordings completed</strong>
        </div>
        <button type="button" className="explorer-disclosure-button expanded" aria-label="Hide line list" title="Hide line list" onClick={onToggleOpen}>
          <span className="context-disclosure" aria-hidden="true" />
        </button>
      </div>
      <label className="item-search">
        <span>Search lines</span>
        <div>
          <input
            type="search"
            value={searchQuery}
            placeholder="Find a cue or line"
            onChange={(event) => setSearchQuery(event.target.value)}
          />
          {searchQuery ? (
            <button type="button" aria-label="Clear line search." onClick={() => setSearchQuery("")}>
              ×
            </button>
          ) : null}
        </div>
      </label>
      <div className="item-list">
        {filteredProgress.length === 0 ? <p className="item-empty">No matching lines.</p> : null}
        {filteredProgress.map(({ item, status }) => (
          <button
            key={item.id}
            ref={item.id === selectedItemId ? selectedRowRef : undefined}
            type="button"
            className={item.id === selectedItemId ? "item-row selected" : "item-row"}
            onClick={() => onSelectItem(item)}
          >
            <span className={status === "accepted" ? "status-dot accepted" : "status-dot"} aria-label={status} title={status} />
            <strong>{item.id}</strong>
            <span>{item.segmentText}</span>
          </button>
        ))}
      </div>
    </aside>
  );
}
