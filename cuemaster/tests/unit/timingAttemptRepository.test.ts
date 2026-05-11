import { afterEach, describe, expect, it } from "vitest";
import type { TimingAttempt } from "../../src/domain/timingAttempt";
import { db } from "../../src/storage/db";
import { timingAttemptRepository } from "../../src/storage/timingAttemptRepository";

describe("timingAttemptRepository", () => {
  afterEach(async () => {
    await db.timingAttempts.clear();
  });

  it("returns the latest attempt for a line", async () => {
    await timingAttemptRepository.save(attempt("first", 1000));
    await timingAttemptRepository.save(attempt("second", 2000));

    expect(await timingAttemptRepository.latestForLine("playbook", "MEGAERA", "line")).toMatchObject({
      id: "second",
      createdAt: 2000
    });
  });

  it("keeps only the most recent attempts for a line", async () => {
    for (let index = 0; index < 25; index += 1) {
      await timingAttemptRepository.save(attempt(`attempt-${index}`, index));
    }

    const attempts = await db.timingAttempts
      .where("[playbookId+roleId+lineId]")
      .equals(["playbook", "MEGAERA", "line"])
      .toArray();

    expect(attempts).toHaveLength(20);
    expect(attempts.some((candidate) => candidate.id === "attempt-0")).toBe(false);
    expect(attempts.some((candidate) => candidate.id === "attempt-24")).toBe(true);
  });
});

function attempt(id: string, createdAt: number): TimingAttempt {
  return {
    id,
    playbookId: "playbook",
    roleId: "MEGAERA",
    lineId: "line",
    createdAt,
    hesitationMs: 500,
    deliveryMs: 1200,
    targetHesitationMs: 500,
    targetDeliveryMs: 1200,
    hesitationLabel: "close",
    deliveryLabel: "close",
    detectionMode: "energy"
  };
}
