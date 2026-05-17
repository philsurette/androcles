import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useTempoTiming } from "../../src/ui/hooks/useTempoTiming";

describe("useTempoTiming", () => {
  it("skips feedback tones when the browser has no audio context", async () => {
    const { result } = renderHook(() => useTempoTiming());

    await expect(
      act(async () => {
        await result.current.playTimingFeedbackTone("retry");
      })
    ).resolves.toBeUndefined();
  });
});
