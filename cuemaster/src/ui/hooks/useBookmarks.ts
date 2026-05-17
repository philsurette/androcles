import { useEffect, useMemo, useState } from "react";
import type { Bookmark } from "../../domain/bookmark";
import type { Line } from "../../domain/line";
import { indexedDbStorage } from "../../storage/indexedDbStorage";
import { userFacingErrorMessage } from "../errors/userFacingErrorMessage";

type UseBookmarksProps = {
  playbookId: string;
  roleId: string;
  roleLines: Line[];
  currentLine: Line | null;
  onStorageStatus: (message: string) => void;
};

export function useBookmarks({
  playbookId,
  roleId,
  roleLines,
  currentLine,
  onStorageStatus
}: UseBookmarksProps) {
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [isCurrentLineBookmarked, setIsCurrentLineBookmarked] = useState(false);
  const bookmarkedLineIds = useMemo(() => new Set(bookmarks.map((bookmark) => bookmark.lineId)), [bookmarks]);

  useEffect(() => {
    void loadCurrentBookmark();
  }, [currentLine?.id, playbookId, roleId]);

  useEffect(() => {
    void loadBookmarks();
  }, [playbookId, roleId]);

  async function loadCurrentBookmark() {
    if (!currentLine) {
      setIsCurrentLineBookmarked(false);
      return;
    }
    try {
      setIsCurrentLineBookmarked(Boolean(await indexedDbStorage.bookmarks.get(playbookId, roleId, currentLine.id)));
    } catch (error) {
      setIsCurrentLineBookmarked(false);
      onStorageStatus(userFacingErrorMessage(error));
    }
  }

  async function loadBookmarks() {
    try {
      setBookmarks(await indexedDbStorage.bookmarks.listForRole(playbookId, roleId));
    } catch (error) {
      setBookmarks([]);
      onStorageStatus(userFacingErrorMessage(error));
    }
  }

  async function toggleBookmark() {
    if (!currentLine) {
      return;
    }
    try {
      if (isCurrentLineBookmarked) {
        await indexedDbStorage.bookmarks.delete(playbookId, roleId, currentLine.id);
        setIsCurrentLineBookmarked(false);
      } else {
        await indexedDbStorage.bookmarks.save({
          id: `${playbookId}:${roleId}:${currentLine.id}`,
          playbookId,
          roleId,
          lineId: currentLine.id,
          createdAt: Date.now()
        });
        setIsCurrentLineBookmarked(true);
      }
      onStorageStatus("");
      await loadBookmarks();
    } catch (error) {
      onStorageStatus(userFacingErrorMessage(error));
    }
  }

  const bookmarkNeighbors = useMemo(() => {
    const lineIndexById = new Map(roleLines.map((playbookLine, index) => [playbookLine.id, index]));
    const orderedBookmarks = bookmarks
      .map((bookmark) => bookmark.lineId)
      .filter((lineId) => lineIndexById.has(lineId))
      .sort((left, right) => (lineIndexById.get(left) ?? 0) - (lineIndexById.get(right) ?? 0));

    if (!currentLine) {
      return { previousLineId: null, nextLineId: null };
    }

    const currentLineIndex = lineIndexById.get(currentLine.id);
    if (currentLineIndex === undefined) {
      return { previousLineId: null, nextLineId: null };
    }

    let previousLineId: string | null = null;
    let nextLineId: string | null = null;
    for (const bookmarkLineId of orderedBookmarks) {
      const bookmarkedLineIndex = lineIndexById.get(bookmarkLineId);
      if (bookmarkedLineIndex === undefined) {
        continue;
      }
      if (bookmarkedLineIndex < currentLineIndex) {
        previousLineId = bookmarkLineId;
      } else if (bookmarkedLineIndex > currentLineIndex && nextLineId === null) {
        nextLineId = bookmarkLineId;
      }
    }

    return { previousLineId, nextLineId };
  }, [bookmarks, currentLine, roleLines]);

  return {
    bookmarks,
    bookmarkedLineIds,
    isCurrentLineBookmarked,
    bookmarkNeighbors,
    loadBookmarks,
    toggleBookmark
  };
}
