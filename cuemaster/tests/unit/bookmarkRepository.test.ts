import { afterEach, describe, expect, it } from "vitest";
import type { Bookmark } from "../../src/domain/bookmark";
import { bookmarkRepository } from "../../src/storage/bookmarkRepository";
import { db } from "../../src/storage/db";

describe("bookmarkRepository", () => {
  afterEach(async () => {
    await db.bookmarks.clear();
  });

  it("saves and gets a bookmark for a line", async () => {
    await bookmarkRepository.save(bookmark("line-one"));

    expect(await bookmarkRepository.get("playbook", "MEGAERA", "line-one")).toMatchObject({
      lineId: "line-one"
    });
  });

  it("lists bookmarks for a role", async () => {
    await bookmarkRepository.save(bookmark("line-one"));
    await bookmarkRepository.save(bookmark("line-two"));
    await bookmarkRepository.save({ ...bookmark("other-role-line"), id: "other", roleId: "ANDROCLES" });

    expect(await bookmarkRepository.listForRole("playbook", "MEGAERA")).toHaveLength(2);
  });

  it("deletes a bookmark for a line", async () => {
    await bookmarkRepository.save(bookmark("line-one"));
    await bookmarkRepository.delete("playbook", "MEGAERA", "line-one");

    expect(await bookmarkRepository.get("playbook", "MEGAERA", "line-one")).toBeUndefined();
  });
});

function bookmark(lineId: string): Bookmark {
  return {
    id: `playbook:MEGAERA:${lineId}`,
    playbookId: "playbook",
    roleId: "MEGAERA",
    lineId,
    createdAt: 1000
  };
}
