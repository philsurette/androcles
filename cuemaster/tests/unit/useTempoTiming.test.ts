import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Line } from "../../src/domain/line";
import { db } from "../../src/storage/db";
import { evaluateTempoTimingResult, useTempoTiming } from "../../src/ui/hooks/useTempoTiming";

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

  it("formats speech-start timing status", () => {
    expect(evaluateTempoTimingResult({
      result: { event: "speech-started", atMs: 1000, hesitationMs: 725 },
      line: lineFixture(),
      tempoTargetHesitationMs: 750,
      practiceTargetPaceMultiplier: 1,
      absoluteTempoForgivenessMs: 500,
      tempoTolerancePercent: 0.2,
      absolutePickupForgivenessMs: 250,
      autoAdvanceMode: "disabled",
      autoPlayLineMode: "disabled",
      tempoTimingEnabled: true,
      atEnd: false
    })).toEqual({
      kind: "speech-started",
      playbackStatus: "Speech detected (725ms pause)."
    });
  });

  it("evaluates delivery timing and auto-repeat decisions", () => {
    const result = evaluateTempoTimingResult({
      result: { event: "delivery-ended", atMs: 5000, hesitationMs: 900, deliveryMs: 3200 },
      line: lineFixture(),
      tempoTargetHesitationMs: 750,
      practiceTargetPaceMultiplier: 1,
      absoluteTempoForgivenessMs: 250,
      tempoTolerancePercent: 0.2,
      absolutePickupForgivenessMs: 250,
      autoAdvanceMode: "when-not-slow",
      autoPlayLineMode: "off-target",
      tempoTimingEnabled: true,
      atEnd: false
    });

    expect(result).toMatchObject({
      kind: "delivery-ended",
      shouldAutoAdvance: false,
      shouldAutoPlayLine: true,
      shouldRepeatCue: true,
      timingStatus: {
        delivery: {
          label: "slow",
          measuredMs: 3200
        }
      }
    });
  });
});

class MockTempoTimingDetector {
  readonly start = vi.fn(async () => {});
  readonly stop = vi.fn();
  readonly beginAttempt = vi.fn();
}

function lineFixture(): Line {
  return {
    id: "line-one",
    partId: 1,
    blockId: "1.1",
    role: "LAVINIA",
    speaker: "LAVINIA",
    contentHash: "sha256:line",
    cue: {
      speaker: "ANDROCLES",
      text: "Cue.",
      audioPath: "audio/cue.wav",
      durationMs: 500
    },
    responseText: "A measured line.",
    responseSegments: [
      {
        id: "line-one-segment",
        segmentId: "I_1_1",
        contentHash: "sha256:segment",
        owners: ["LAVINIA"],
        text: "A measured line.",
        audioPath: "audio/line.wav",
        durationMs: 2000,
        simultaneous: false
      }
    ],
    directions: [],
    previousRoles: []
  };
}
