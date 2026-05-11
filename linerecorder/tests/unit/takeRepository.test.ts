import { beforeEach, describe, expect, it } from "vitest";
import type { RecordingTake } from "../../src/domain/take";
import { db } from "../../src/storage/db";
import { takeRepository } from "../../src/storage/takeRepository";

describe("TakeRepository", () => {
  beforeEach(async () => {
    await db.projects.clear();
    await db.takes.clear();
  });

  it("keeps only one accepted take for a segment", async () => {
    await takeRepository.saveAccepted(takeFixture("take-1"));
    await takeRepository.saveAccepted(takeFixture("take-2"));

    const takes = await db.takes.orderBy("id").toArray();
    expect(takes.map((take) => [take.id, take.status])).toEqual([
      ["take-1", "replaced"],
      ["take-2", "accepted"]
    ]);
  });

  it("loads the accepted take for a segment", async () => {
    await takeRepository.saveAccepted(takeFixture("take-1"));

    await expect(takeRepository.acceptedForSegment("androcles:CENTURION", "0_12_1")).resolves.toMatchObject({
      id: "take-1",
      status: "accepted"
    });
  });
});

function takeFixture(id: string): RecordingTake {
  return {
    id,
    projectId: "androcles:CENTURION",
    segmentId: "0_12_1",
    status: "accepted",
    recordedAt: "2026-05-11T12:00:00Z",
    durationMs: 1000,
    sampleRateHz: 48000,
    channels: 1,
    blob: new Blob(["fake wav"], { type: "audio/wav" })
  };
}
