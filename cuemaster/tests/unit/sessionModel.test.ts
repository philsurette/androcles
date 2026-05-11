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
      playbackRate: 1,
      speakAlongEnabled: false,
      tempoTimingPreferred: true,
      updatedAt: 1000
    };

    expect(session.tempoTimingPreferred).toBe(true);
    expect("tempoTimingEnabled" in session).toBe(false);
  });
});
