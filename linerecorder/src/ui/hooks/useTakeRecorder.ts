import { useEffect, useRef, useState } from "react";
import { WavRecorder, type RecordedWav, type WavRecorderReading } from "../../audio/wavRecorder";
import type { RecordingItem } from "../../domain/recordingItem";
import type { RecordingTake } from "../../domain/take";
import type { RecordingProjectRecord } from "../../storage/db";
import { indexedDbStorage } from "../../storage/indexedDbStorage";
import type { TakeRepository } from "../../storage/takeRepository";
import type { MicrophoneConfig } from "../microphoneConfig";

type UseTakeRecorderProps = {
  project: RecordingProjectRecord;
  item: RecordingItem;
  microphoneConfig: MicrophoneConfig | null;
  onAccepted: () => Promise<void>;
  takes?: TakeRepository;
};

export function useTakeRecorder({
  project,
  item,
  microphoneConfig,
  onAccepted,
  takes = indexedDbStorage.takes
}: UseTakeRecorderProps) {
  const recorderRef = useRef<WavRecorder | null>(null);
  const playbackUrlRef = useRef<string | null>(null);
  const playbackAudioRef = useRef<HTMLAudioElement | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [currentTake, setCurrentTake] = useState<RecordedWav | null>(null);
  const [acceptedTake, setAcceptedTake] = useState<RecordingTake | null>(null);
  const [recordingReading, setRecordingReading] = useState<WavRecorderReading>({ energy: 0, level: "no-signal" });
  const [playingSource, setPlayingSource] = useState<"take" | "saved" | null>(null);
  const [status, setStatus] = useState("Checking saved take...");
  const [statusTone, setStatusTone] = useState<"normal" | "warning">("normal");

  useEffect(() => {
    return () => {
      recorderRef.current?.stopWithoutResult();
      stopPlayback();
    };
  }, []);

  useEffect(() => {
    recorderRef.current?.stopWithoutResult();
    setIsRecording(false);
    setCurrentTake(null);
    setAcceptedTake(null);
    setRecordingReading({ energy: 0, level: "no-signal" });
    setStatus("Checking saved take...");
    setStatusTone("normal");
    stopPlayback();
    void loadAcceptedTake();
  }, [project.id, item.id, takes]);

  useEffect(() => {
    if (microphoneConfig && statusTone === "warning" && status === "Start microphone setup before recording.") {
      setStatus(currentTake ? "Ready to accept or discard take." : acceptedTake ? `Accepted take saved: ${Math.round(acceptedTake.durationMs)} ms.` : "Ready to record.");
      setStatusTone("normal");
    }
  }, [microphoneConfig, status, statusTone, currentTake, acceptedTake]);

  async function loadAcceptedTake(): Promise<void> {
    const take = await takes.acceptedForSegment(project.id, item.id);
    setAcceptedTake(take ?? null);
    setStatus(take ? `Accepted take saved: ${Math.round(take.durationMs)} ms.` : "No take recorded.");
    setStatusTone("normal");
  }

  async function startRecording(): Promise<void> {
    if (!microphoneConfig) {
      setStatus("Start microphone setup before recording.");
      setStatusTone("warning");
      return;
    }
    try {
      stopPlayback();
      const recorder = new WavRecorder(setRecordingReading);
      recorderRef.current = recorder;
      setCurrentTake(null);
      setRecordingReading({ energy: 0, level: "no-signal" });
      setStatus("Recording...");
      setStatusTone("normal");
      await recorder.start(microphoneConfig.deviceId, microphoneConfig.mode);
      setIsRecording(true);
    } catch {
      setStatus("Unable to start recording.");
      setStatusTone("warning");
      setIsRecording(false);
    }
  }

  function stopRecording(): void {
    if (!recorderRef.current) {
      return;
    }
    const take = recorderRef.current.stop();
    recorderRef.current = null;
    setCurrentTake(take);
    setIsRecording(false);
    setRecordingReading({ energy: 0, level: "no-signal" });
    setStatus(`Recorded ${Math.round(take.durationMs)} ms.`);
    setStatusTone("normal");
  }

  function playTake(): void {
    if (!currentTake) {
      return;
    }
    playBlob(currentTake.blob, "take");
  }

  function playAcceptedTake(): void {
    if (!acceptedTake) {
      return;
    }
    playBlob(acceptedTake.blob, "saved");
  }

  async function acceptTake(): Promise<void> {
    if (!currentTake) {
      return;
    }
    const take: RecordingTake = {
      id: `${project.id}:${item.id}:${new Date().toISOString()}`,
      projectId: project.id,
      segmentId: item.id,
      status: "accepted",
      recordedAt: new Date().toISOString(),
      durationMs: currentTake.durationMs,
      sampleRateHz: currentTake.sampleRateHz,
      channels: currentTake.channels,
      inputQuality: {
        peakEnergy: currentTake.inputQuality.peakEnergy,
        levelCounts: {
          noSignal: currentTake.inputQuality.levelCounts["no-signal"],
          tooQuiet: currentTake.inputQuality.levelCounts["too-quiet"],
          good: currentTake.inputQuality.levelCounts.good,
          clipping: currentTake.inputQuality.levelCounts.clipping
        }
      },
      blob: currentTake.blob
    };
    await takes.saveAccepted(take);
    setAcceptedTake(take);
    setCurrentTake(null);
    setStatus("Take accepted.");
    setStatusTone("normal");
    await onAccepted();
  }

  function discardTake(): void {
    setCurrentTake(null);
    setRecordingReading({ energy: 0, level: "no-signal" });
    setStatus(acceptedTake ? `Accepted take saved: ${Math.round(acceptedTake.durationMs)} ms.` : "No take recorded.");
    setStatusTone("normal");
    stopPlayback();
  }

  function stopPlayback(): void {
    if (playbackAudioRef.current) {
      playbackAudioRef.current.pause();
      playbackAudioRef.current.currentTime = 0;
      playbackAudioRef.current = null;
    }
    if (playbackUrlRef.current) {
      URL.revokeObjectURL(playbackUrlRef.current);
      playbackUrlRef.current = null;
    }
    setPlayingSource(null);
  }

  function playBlob(blob: Blob, source: "take" | "saved"): void {
    stopPlayback();
    const url = URL.createObjectURL(blob);
    playbackUrlRef.current = url;
    const audio = new Audio(url);
    playbackAudioRef.current = audio;
    setPlayingSource(source);
    audio.onended = stopPlayback;
    audio.onerror = stopPlayback;
    void audio.play();
  }

  return {
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
  };
}
