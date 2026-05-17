import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { db } from "../../src/storage/db";
import { useRehearsalSessionPersistence } from "../../src/ui/hooks/useRehearsalSessionPersistence";

describe("useRehearsalSessionPersistence", () => {
  afterEach(async () => {
    await db.sessions.clear();
  });

  it("saves rehearsal sessions with current defaults", async () => {
    const storageStatuses: string[] = [];
    const { result } = renderHook(() => useRehearsalSessionPersistence({
      playbookId: "playbook",
      roleId: "LAVINIA",
      playbackRate: 1.3,
      speakAlongEnabled: false,
      tempoTimingPreferred: true,
      isLineRevealed: true,
      cueWindowPresetId: "last_5s",
      includeDirections: true,
      showLinesByDefault: true,
      speakAlongPauseMs: 750,
      tempoTargetHesitationMs: 800,
      syncPracticeTiming: false,
      includeBlocking: true,
      blockingScope: "all",
      practiceTargetPaceMultiplier: 1.2,
      syncSpeakAlongSpeed: false,
      absoluteTempoForgivenessMs: 500,
      tempoTolerancePercent: 0.2,
      absolutePickupForgivenessMs: 300,
      autoAdvanceMode: "disabled",
      autoPlayLineMode: "always",
      rehearsalTextSize: "large",
      tempoEndOfLineSilenceMs: 1500,
      onStorageStatus: (message) => storageStatuses.push(message)
    }));

    await result.current.saveSession(3);

    const sessions = await db.sessions.toArray();
    expect(storageStatuses).toEqual([""]);
    expect(sessions).toMatchObject([
      {
        playbookId: "playbook",
        roleId: "LAVINIA",
        lineIndex: 3,
        playbackRate: 1.3,
        cueWindowPresetId: "last_5s",
        includeBlocking: true,
        blockingScope: "all",
        autoAdvanceMode: "disabled",
        autoPlayLineMode: "disabled",
        rehearsalTextSize: "large"
      }
    ]);
  });
});
