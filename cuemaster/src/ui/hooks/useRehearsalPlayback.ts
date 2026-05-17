import { useEffect, useState } from "react";
import { AudioQueue, type QueueItem } from "../../rehearsal/audioQueue";
import { userFacingErrorMessage } from "../errors/userFacingErrorMessage";

export type PlaybackUiState = "idle" | "playing" | "paused";
export type PlaybackSource = "cue" | "line";
export type RehearsalAudioQueue = {
  play(items: QueueItem[]): Promise<void>;
  pause(): void;
  resume(): void;
  cancel(): void;
};

type PlaybackRunOptions = {
  source: PlaybackSource | null;
  startStatus?: string;
  completeStatus?: string;
  onComplete?: () => void;
};

export function useRehearsalPlayback(
  playbookId: string,
  createAudioQueue: (playbookId: string) => RehearsalAudioQueue = (id) => new AudioQueue(id)
) {
  const [audioQueue] = useState(() => createAudioQueue(playbookId));
  const [playbackState, setPlaybackState] = useState<PlaybackUiState>("idle");
  const [playbackSource, setPlaybackSource] = useState<PlaybackSource | null>(null);
  const [playbackStatus, setPlaybackStatus] = useState<string>("");

  useEffect(() => {
    return () => {
      audioQueue.cancel();
    };
  }, [audioQueue]);

  async function playItems(items: QueueItem[], options: PlaybackRunOptions): Promise<boolean> {
    setPlaybackSource(options.source);
    if (options.startStatus !== undefined) {
      setPlaybackStatus(options.startStatus);
    }
    setPlaybackState("playing");
    try {
      await audioQueue.play(items);
      if (options.completeStatus !== undefined) {
        setPlaybackStatus(options.completeStatus);
      }
      setPlaybackState("idle");
      setPlaybackSource(null);
      options.onComplete?.();
      return true;
    } catch (error) {
      setPlaybackState("idle");
      setPlaybackSource(null);
      setPlaybackStatus(userFacingErrorMessage(error));
      return false;
    }
  }

  function pausePlayback() {
    if (playbackState !== "playing") {
      return;
    }
    audioQueue.pause();
    setPlaybackState("paused");
    setPlaybackStatus("Playback paused.");
  }

  function resumePlayback() {
    if (playbackState !== "paused") {
      return;
    }
    audioQueue.resume();
    setPlaybackState("playing");
    setPlaybackStatus("Playback resumed.");
  }

  function stopPlayback(status = "Playback stopped.") {
    audioQueue.cancel();
    setPlaybackState("idle");
    setPlaybackSource(null);
    setPlaybackStatus(status);
  }

  return {
    audioQueue,
    playbackState,
    playbackSource,
    playbackStatus,
    setPlaybackState,
    setPlaybackSource,
    setPlaybackStatus,
    playItems,
    pausePlayback,
    resumePlayback,
    stopPlayback
  };
}
