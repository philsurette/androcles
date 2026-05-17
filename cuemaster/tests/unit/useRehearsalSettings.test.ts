import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RehearsalSession } from "../../src/domain/session";
import { useRehearsalSettings } from "../../src/ui/hooks/useRehearsalSettings";

describe("useRehearsalSettings", () => {
  it("uses persisted session values", () => {
    const { result } = renderHook(() => useRehearsalSettings(sessionFixture(), false));

    expect(result.current.playbackRate).toBe(1.3);
    expect(result.current.cueWindowPresetId).toBe("last_5s");
    expect(result.current.showLinesByDefault).toBe(true);
    expect(result.current.isLineRevealed).toBe(true);
    expect(result.current.includeDirections).toBe(false);
    expect(result.current.includeBlocking).toBe(false);
    expect(result.current.blockingScope).toBe("all");
    expect(result.current.speakAlongEnabled).toBe(true);
    expect(result.current.speakAlongPauseMs).toBe(700);
    expect(result.current.tempoTargetHesitationMs).toBe(900);
    expect(result.current.syncPracticeTiming).toBe(false);
    expect(result.current.syncSpeakAlongSpeed).toBe(false);
    expect(result.current.absoluteTempoForgivenessMs).toBe(450);
    expect(result.current.absolutePickupForgivenessMs).toBe(300);
    expect(result.current.tempoTolerancePercent).toBe(0.2);
    expect(result.current.tempoEndOfLineSilenceMs).toBe(1000);
    expect(result.current.autoAdvanceMode).toBe("when-not-slow");
    expect(result.current.autoPlayLineMode).toBe("off-target");
    expect(result.current.rehearsalTextSize).toBe("large");
    expect(result.current.tempoTimingEnabled).toBe(true);
    expect(result.current.tempoTimingPreferred).toBe(true);
  });

  it("normalizes disabled autoadvance to disable autoplay", () => {
    const session = {
      ...sessionFixture(),
      autoAdvanceMode: "disabled",
      autoPlayLineMode: "always"
    } satisfies RehearsalSession;

    const { result } = renderHook(() => useRehearsalSettings(session, true));

    expect(result.current.autoAdvanceMode).toBe("disabled");
    expect(result.current.autoPlayLineMode).toBe("disabled");
  });
});

function sessionFixture(): RehearsalSession {
  return {
    playbookId: "androcles",
    roleId: "LAVINIA",
    lineIndex: 2,
    cueDepth: 1,
    includeDirections: false,
    includeBlocking: false,
    blockingScope: "all",
    revealLine: false,
    showLinesByDefault: true,
    cueWindowPresetId: "last_5s",
    playbackRate: 1.25,
    speakAlongEnabled: true,
    speakAlongPauseMs: 700,
    tempoTargetHesitationMs: 900,
    practiceTargetPaceMultiplier: 1.3,
    syncSpeakAlongSpeed: false,
    absoluteTempoForgivenessMs: 450,
    absolutePickupForgivenessMs: 300,
    tempoTolerancePercent: 0.2,
    tempoEndOfLineSilenceMs: 1200,
    syncPracticeTiming: false,
    tempoTimingPreferred: true,
    autoAdvanceMode: "when-not-slow",
    autoPlayLineMode: "off-target",
    rehearsalTextSize: "large",
    updatedAt: 1
  };
}
