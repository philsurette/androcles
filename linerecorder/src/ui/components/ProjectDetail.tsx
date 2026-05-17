import { useState } from "react";
import { meterFillPercentForLevel } from "../../audio/inputMeter";
import type { MicrophoneReading } from "../../audio/microphoneSession";
import type { RecordingItem } from "../../domain/recordingItem";
import { recordingItemProgress } from "../../domain/recordingItemStatus";
import { nextProgress, previousProgress, selectedProgressIndex } from "../../domain/recordingNavigation";
import type { RecordingProjectRecord } from "../../storage/db";
import type { MicrophoneConfig } from "../microphoneConfig";
import { levelLabel } from "../recordingItemPresentation";
import { ItemDetail } from "./ItemDetail";
import { ItemList } from "./ItemList";
import { MicrophoneSetup } from "./MicrophoneSetup";
import { ProjectSummary } from "./ProjectSummary";

type ProjectDetailProps = {
  project: RecordingProjectRecord;
  acceptedItemIds: Set<string>;
  status: string;
  onSelectItem: (item: RecordingItem) => void;
  onAccepted: () => Promise<void>;
  onExport: () => void;
  onViewInfo: (item?: RecordingItem) => void;
  onBack: () => void;
  isExporting: boolean;
};

export function ProjectDetail({
  project,
  acceptedItemIds,
  status,
  onSelectItem,
  onAccepted,
  onExport,
  onBack,
  onViewInfo,
  isExporting
}: ProjectDetailProps) {
  const [microphoneConfig, setMicrophoneConfig] = useState<MicrophoneConfig | null>(null);
  const [microphoneReading, setMicrophoneReading] = useState<MicrophoneReading>({ energy: 0, level: "no-signal" });
  const [isExplorerOpen, setIsExplorerOpen] = useState(false);
  const [isMicrophoneSetupOpen, setIsMicrophoneSetupOpen] = useState(false);
  const progress = recordingItemProgress(project.request.items, acceptedItemIds);
  const selectedIndex = selectedProgressIndex(progress, project.currentItemId);
  const selectedItem = selectedIndex === -1 ? undefined : progress[selectedIndex];
  const previousItem = previousProgress(progress, selectedIndex);
  const nextItem = nextProgress(progress, selectedIndex);

  if (isMicrophoneSetupOpen) {
    return (
      <section className="project-detail microphone-config-page" aria-label="Microphone setup">
        <div className="summary-title">
          <div className="summary-title-main">
            <button type="button" className="secondary icon-button summary-back-button" onClick={() => setIsMicrophoneSetupOpen(false)}>
              <span aria-hidden="true">←</span>
              <span className="visually-hidden">Back</span>
            </button>
            <div className="summary-title-text">
              <p className="eyebrow">Microphone</p>
              <h2>Microphone setup</h2>
            </div>
          </div>
        </div>
        <MicrophoneSetup
          project={project}
          onReady={setMicrophoneConfig}
          onReading={setMicrophoneReading}
          onDone={() => setIsMicrophoneSetupOpen(false)}
        />
      </section>
    );
  }

  return (
    <section className="project-detail recording-page" aria-label="Recording Request detail">
      <ProjectSummary
        project={project}
        progress={progress}
        onExport={onExport}
        onViewInfo={onViewInfo}
        onBack={onBack}
        isExplorerOpen={isExplorerOpen}
        onToggleExplorer={() => setIsExplorerOpen((current) => !current)}
        isExporting={isExporting}
      />
      <MicrophoneStrip config={microphoneConfig} reading={microphoneReading} onOpen={() => setIsMicrophoneSetupOpen(true)} />
      <div className={isExplorerOpen ? "recording-workspace" : "recording-workspace explorer-collapsed"}>
        <ItemList
          progress={progress}
          selectedItemId={selectedItem?.item.id}
          isOpen={isExplorerOpen}
          onToggleOpen={() => setIsExplorerOpen((current) => !current)}
          onSelectItem={onSelectItem}
        />
        {selectedItem ? (
          <ItemDetail
            project={project}
            progress={selectedItem}
            itemNumber={selectedIndex + 1}
            itemCount={progress.length}
            microphoneConfig={microphoneConfig}
            previousItem={previousItem}
            nextItem={nextItem}
            onNavigate={onSelectItem}
            onAccepted={onAccepted}
          />
        ) : null}
      </div>
    </section>
  );
}

type MicrophoneStripProps = {
  config: MicrophoneConfig | null;
  reading: MicrophoneReading;
  onOpen: () => void;
};

function MicrophoneStrip({ config, reading, onOpen }: MicrophoneStripProps) {
  const label = config ? "Mic Ready" : "Start Mic";

  return (
    <section className="microphone-strip" aria-label="Microphone">
      <span className={config ? "microphone-glyph active" : "microphone-glyph"} aria-label="Microphone">
        🎙
      </span>
      <div className="meter-row">
        <div className="meter" aria-label={`Input level: ${levelLabel(reading.level)}`}>
          <span style={{ width: `${meterFillPercentForLevel(reading.energy, reading.level)}%` }} />
        </div>
        <span className={`meter-label ${reading.level}`}>{levelLabel(reading.level)}</span>
      </div>
      <button type="button" className={config ? "secondary" : "button"} onClick={onOpen}>
        {label}
      </button>
    </section>
  );
}
