import { act, renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { QueueItem } from "../../src/rehearsal/audioQueue";
import { useRehearsalPlayback, type RehearsalAudioQueue } from "../../src/ui/hooks/useRehearsalPlayback";

describe("useRehearsalPlayback", () => {
  it("tracks successful queue playback", async () => {
    const queue = new MockAudioQueue();
    const { result } = renderHook(() => useRehearsalPlayback("playbook", () => queue));
    const items: QueueItem[] = [{ kind: "audio", path: "line.wav", playbackRate: 1 }];

    await act(async () => {
      const didComplete = await result.current.playItems(items, {
        source: "line",
        startStatus: "Playing your line...",
        completeStatus: "Line complete."
      });
      expect(didComplete).toBe(true);
    });

    expect(queue.playCalls).toEqual([items]);
    expect(result.current.playbackState).toBe("idle");
    expect(result.current.playbackSource).toBe(null);
    expect(result.current.playbackStatus).toBe("Line complete.");
  });

  it("pauses, resumes, and stops the queue", async () => {
    const queue = new MockAudioQueue();
    queue.playImplementation = () => new Promise(() => {});
    const { result } = renderHook(() => useRehearsalPlayback("playbook", () => queue));

    await act(async () => {
      void result.current.playItems([{ kind: "audio", path: "cue.wav", playbackRate: 1 }], { source: "cue" });
    });
    act(() => result.current.pausePlayback());
    expect(queue.pause).toHaveBeenCalledOnce();
    expect(result.current.playbackState).toBe("paused");

    act(() => result.current.resumePlayback());
    expect(queue.resume).toHaveBeenCalledOnce();
    expect(result.current.playbackState).toBe("playing");

    act(() => result.current.stopPlayback());
    expect(queue.cancel).toHaveBeenCalledOnce();
    expect(result.current.playbackState).toBe("idle");
    expect(result.current.playbackSource).toBe(null);
    expect(result.current.playbackStatus).toBe("Playback stopped.");
  });

  it("surfaces queue playback errors as status text", async () => {
    const queue = new MockAudioQueue();
    queue.playImplementation = async () => {
      throw new Error("Audio missing.");
    };
    const { result } = renderHook(() => useRehearsalPlayback("playbook", () => queue));

    await act(async () => {
      const didComplete = await result.current.playItems([{ kind: "audio", path: "missing.wav", playbackRate: 1 }], { source: "cue" });
      expect(didComplete).toBe(false);
    });

    expect(result.current.playbackState).toBe("idle");
    expect(result.current.playbackSource).toBe(null);
    expect(result.current.playbackStatus).toBe("Audio missing.");
  });
});

class MockAudioQueue implements RehearsalAudioQueue {
  readonly playCalls: QueueItem[][] = [];
  readonly pause = vi.fn();
  readonly resume = vi.fn();
  readonly cancel = vi.fn();
  playImplementation: (items: QueueItem[]) => Promise<void> = async () => {};

  async play(items: QueueItem[]): Promise<void> {
    this.playCalls.push(items);
    await this.playImplementation(items);
  }
}
