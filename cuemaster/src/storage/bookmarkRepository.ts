import Dexie from "dexie";
import type { Bookmark } from "../domain/bookmark";
import { db } from "./db";
import type { BookmarkRepository } from "./storage";

export const bookmarkRepository: BookmarkRepository = {
  get: (playbookId: string, roleId: string, lineId: string) =>
    db.bookmarks.get([playbookId, roleId, lineId]),

  listForRole: (playbookId: string, roleId: string) =>
    db.bookmarks
      .where("[playbookId+roleId+lineId]")
      .between([playbookId, roleId, Dexie.minKey], [playbookId, roleId, Dexie.maxKey])
      .toArray(),

  save: (bookmark: Bookmark) => db.bookmarks.put(bookmark),

  delete: (playbookId: string, roleId: string, lineId: string) =>
    db.bookmarks.delete([playbookId, roleId, lineId]),

  deleteForPlaybook: (playbookId: string) => db.bookmarks.where("playbookId").equals(playbookId).delete()
};
