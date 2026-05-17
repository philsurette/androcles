import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { db } from "../../src/storage/db";
import { useTempoTiming } from "../../src/ui/hooks/useTempoTiming";

describe("useTempoTiming", () => {
  afterEach(async () => {
    await db.timingAttempts.clear();
  });

  it("skips feedback tones when the browser has no audio context", async () => {
    const { result } = renderHook(() => useTempoTiming());

    await expect(
      act(async () => {
        await result.current.playTimingFeedbackTone("retry");
      })
    ).resolves.toBeUndefined();
  });

  it("saves delivery timing attempts and reloads review attempts", async () => {
    vi.spyOn(crypto, "randomUUID").mockReturnValue("attempt-id" as `${string}-${string}-${string}-${string}-${string}`);
    const storageStatuses: string[] = [];
    const { result } = renderHook(() => useTempoTiming({
      playbookId: "playbook",
      roleId: "LAVINIA",
      onStorageStatus: (message) => storageStatuses.push(message)
    }));

    await act(async () => {
      await result.current.saveTimingAttempt("line-one", {
        hesitation: {
          measuredMs: 400,
          targetMs: 500,
          label: "close"
        },
        delivery: {
          measuredMs: 1200,
          targetMs: 1300,
          label: "close"
        }
      });
    });

    expect(storageStatuses).toEqual([""]);
    expect(result.current.reviewAttempts).toMatchObject([
      {
        id: "attempt-id",
        playbookId: "playbook",
        roleId: "LAVINIA",
        lineId: "line-one",
        hesitationMs: 400,
        deliveryMs: 1200,
        detectionMode: "energy"
      }
    ]);
  });

  it("starts and stops voice activity detectors", async () => {
    const firstDetector = new MockTempoTimingDetector();
    const secondDetector = new MockTempoTimingDetector();
    const { result } = renderHook(() => useTempoTiming());

    await act(async () => {
      expect(await result.current.startVoiceActivityDetector(() => firstDetector)).toBe(firstDetector);
    });
    await act(async () => {
      expect(await result.current.startVoiceActivityDetector(() => secondDetector)).toBe(secondDetector);
    });
    act(() => result.current.stopVoiceActivityDetector());

    expect(firstDetector.start).toHaveBeenCalledOnce();
    expect(firstDetector.stop).toHaveBeenCalledOnce();
    expect(secondDetector.start).toHaveBeenCalledOnce();
    expect(secondDetector.stop).toHaveBeenCalledOnce();
  });
});

class MockTempoTimingDetector {
  readonly start = vi.fn(async () => {});
  readonly stop = vi.fn();
  readonly beginAttempt = vi.fn();
}
