import { useEffect, useRef, useState } from "react";
import { meterFillPercentForLevel } from "../../audio/inputMeter";
import { MicrophoneSession, type MicrophoneReading } from "../../audio/microphoneSession";
import { WavRecorder } from "../../audio/wavRecorder";
import type { FloorNoiseRecording } from "../../domain/floorNoiseRecording";
import { listMicrophoneDevices, MicrophonePermissionError, type MicrophoneDevice, type MicrophoneMode } from "../../platform/microphone";
import type { RecordingProjectRecord } from "../../storage/db";
import type { FloorNoiseRepository } from "../../storage/floorNoiseRepository";
import { indexedDbStorage } from "../../storage/indexedDbStorage";
import type { MicrophoneConfig } from "../microphoneConfig";
import {
  isUsableFloorNoise,
  levelLabel,
  levelStatus,
  recordingInputQuality
} from "../recordingItemPresentation";

type MicrophoneSetupProps = {
  project: RecordingProjectRecord;
  onReady: (config: MicrophoneConfig | null) => void;
  onReading: (reading: MicrophoneReading) => void;
  onDone: () => void;
  floorNoise?: FloorNoiseRepository;
};

export function MicrophoneSetup({
  project,
  onReady,
  onReading,
  onDone,
  floorNoise = indexedDbStorage.floorNoise
}: MicrophoneSetupProps) {
  const sessionRef = useRef<MicrophoneSession | null>(null);
  const floorNoiseRecorderRef = useRef<WavRecorder | null>(null);
  const [devices, setDevices] = useState<MicrophoneDevice[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [mode, setMode] = useState<MicrophoneMode>("clean");
  const [reading, setReading] = useState<MicrophoneReading>({ energy: 0, level: "no-signal" });
  const [status, setStatus] = useState("Microphone not started.");
  const [isActive, setIsActive] = useState(false);
  const [isCapturingFloorNoise, setIsCapturingFloorNoise] = useState(false);

  useEffect(() => {
    onReading(reading);
  }, [reading, onReading]);

  useEffect(() => {
    return () => {
      sessionRef.current?.stop();
      floorNoiseRecorderRef.current?.stopWithoutResult();
    };
  }, []);

  async function refreshDevices(): Promise<void> {
    const availableDevices = await listMicrophoneDevices();
    setDevices(availableDevices);
    if (!selectedDeviceId && availableDevices[0]) {
      setSelectedDeviceId(availableDevices[0].deviceId);
    }
  }

  async function startMicrophone(): Promise<void> {
    try {
      setStatus("Requesting microphone permission...");
      await refreshDevices();
      const session = new MicrophoneSession((nextReading) => {
        setReading(nextReading);
        setStatus(levelStatus(nextReading.level));
      });
      sessionRef.current = session;
      await session.start(selectedDeviceId, mode);
      onReady({ deviceId: selectedDeviceId, deviceLabel: selectedDeviceLabel(), mode });
      setIsActive(true);
    } catch (error) {
      const message =
        error instanceof MicrophonePermissionError ? error.message : "Unable to start microphone setup.";
      setStatus(message);
      setIsActive(false);
    }
  }

  function stopMicrophone(): void {
    floorNoiseRecorderRef.current?.stopWithoutResult();
    floorNoiseRecorderRef.current = null;
    sessionRef.current?.stop();
    sessionRef.current = null;
    onReady(null);
    setIsActive(false);
    setIsCapturingFloorNoise(false);
    setReading({ energy: 0, level: "no-signal" });
    setStatus("Microphone stopped.");
    onReading({ energy: 0, level: "no-signal" });
  }

  async function captureFloorNoise(): Promise<void> {
    if (!isActive) {
      return;
    }
    try {
      setIsCapturingFloorNoise(true);
      setStatus("Stay silent...");
      const recorder = new WavRecorder();
      floorNoiseRecorderRef.current = recorder;
      await recorder.start(selectedDeviceId, mode);
      await sleep(5000);
      const recorded = recorder.stop();
      floorNoiseRecorderRef.current = null;
      if (!isUsableFloorNoise(recorded)) {
        setStatus("Room tone was too loud. Try again while silent.");
        return;
      }
      const recordedAt = new Date().toISOString();
      const floorNoiseRecording: FloorNoiseRecording = {
        id: `floor-${recordedAt.replace(/[-:.]/g, "").replace("Z", "Z")}`,
        projectId: project.id,
        recordedAt,
        durationMs: recorded.durationMs,
        sampleRateHz: recorded.sampleRateHz,
        channels: recorded.channels,
        deviceId: selectedDeviceId,
        deviceLabel: selectedDeviceLabel(),
        mode,
        inputQuality: recordingInputQuality(recorded),
        blob: recorded.blob
      };
      await floorNoise.save(floorNoiseRecording);
      setStatus(`Room tone captured ${new Date(recordedAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}.`);
    } catch {
      floorNoiseRecorderRef.current?.stopWithoutResult();
      floorNoiseRecorderRef.current = null;
      setStatus("Unable to capture room tone.");
    } finally {
      setIsCapturingFloorNoise(false);
    }
  }

  function selectedDeviceLabel(): string {
    return devices.find((device) => device.deviceId === selectedDeviceId)?.label || "Default microphone";
  }

  const showStatus =
    status === "Requesting microphone permission..." ||
    status === "Unable to start microphone setup." ||
    status === "Stay silent..." ||
    status.startsWith("Room tone") ||
    status === "Unable to capture room tone." ||
    status.startsWith("Microphone access");

  return (
    <section className="microphone-panel compact" aria-label="Microphone setup">
      <div className="microphone-heading">
        <span className={isActive ? "microphone-glyph active" : "microphone-glyph"} aria-label={isActive ? "Microphone ready" : "Microphone setup"}>
          🎙
        </span>
        <div className="microphone-actions">
          <button type="button" className="secondary" onClick={onDone}>
            OK
          </button>
        </div>
      </div>
      <div className="microphone-controls">
        <label>
          <span className="visually-hidden">Input</span>
          <select
            value={selectedDeviceId}
            disabled={isActive && isCapturingFloorNoise}
            onFocus={() => void refreshDevices()}
            onChange={(event) => setSelectedDeviceId(event.target.value)}
          >
            {devices.length === 0 ? <option value="">Default microphone</option> : null}
            {devices.map((device) => (
              <option key={device.deviceId} value={device.deviceId}>
                {device.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="visually-hidden">Mode</span>
          <select
            value={mode}
            disabled={isActive && isCapturingFloorNoise}
            onChange={(event) => setMode(event.target.value as MicrophoneMode)}
          >
            <option value="clean">Clean room</option>
            <option value="noisy">Noisy room</option>
          </select>
        </label>
        {isActive ? (
          <button type="button" className="secondary" onClick={stopMicrophone} disabled={isCapturingFloorNoise}>
            Stop Mic
          </button>
        ) : (
          <button type="button" onClick={() => void startMicrophone()}>
            Start Mic
          </button>
        )}
        <button
          type="button"
          className="secondary"
          disabled={!isActive || isCapturingFloorNoise}
          onClick={() => void captureFloorNoise()}
        >
          {isCapturingFloorNoise ? "Capturing..." : "Room Tone"}
        </button>
      </div>
      <div className="meter-row">
        <div className="meter" aria-label={`Input level: ${levelLabel(reading.level)}`}>
          <span style={{ width: `${meterFillPercentForLevel(reading.energy, reading.level)}%` }} />
        </div>
        <span className={`meter-label ${reading.level}`}>{levelLabel(reading.level)}</span>
      </div>
      {showStatus ? <p className="microphone-status">{status}</p> : null}
    </section>
  );
}

function sleep(durationMs: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, durationMs));
}
