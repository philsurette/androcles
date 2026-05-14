import { describe, expect, it } from "vitest";
import type { RehearsalSession } from "../../src/domain/session";

describe("RehearsalSession", () => {
  it("stores tempo timing as a preference, not active microphone state", () => {
    const session: RehearsalSession = {
      playbookId: "playbook",
      roleId: "MEGAERA",
      lineIndex: 0,
      cueDepth: 1,
      includeDirections: true,
      revealLine: false,
      showLinesByDefault: false,
      cueWindowPresetId: "full",
      playbackRate: 1,
      speakAlongEnabled: false,
      speakAlongPauseMs: 750,
      tempoTargetHesitationMs: 750,
      practiceTargetPaceMultiplier: 1,
      syncPracticeTiming: true,
      tempoTimingPreferred: true,
      updatedAt: 1000
    };

    expect(session.tempoTimingPreferred).toBe(true);
    expect(session.practiceTargetPaceMultiplier).toBe(1);
    expect("tempoTimingEnabled" in session).toBe(false);
  });
});
