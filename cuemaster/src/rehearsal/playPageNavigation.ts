import type { Section } from "../domain/section";
import type { PlayPageEntry } from "./playPageEntries";

export type SectionWindow = {
  start: number;
  end: number;
  label: string;
};

export function previousLineIndex(entries: PlayPageEntry[], index: number): number {
  return index > 0 && entries.length > 0 ? index - 1 : -1;
}

export function nextLineIndex(entries: PlayPageEntry[], index: number): number {
  return index >= 0 && index < entries.length - 1 ? index + 1 : -1;
}

export function previousRoleLineIndex(entries: PlayPageEntry[], index: number, role?: string): number {
  if (!role) {
    return -1;
  }
  const targetRole = canonicalRoleKey(role);
  for (let entryIndex = index - 1; entryIndex >= 0; entryIndex -= 1) {
    const entry = entries[entryIndex];
    if (canonicalRoleKey(entry?.speaker) === targetRole) {
      return entryIndex;
    }
  }
  return -1;
}

export function nextRoleLineIndex(entries: PlayPageEntry[], index: number, role?: string): number {
  if (!role) {
    return -1;
  }
  const targetRole = canonicalRoleKey(role);
  for (let entryIndex = index + 1; entryIndex < entries.length; entryIndex += 1) {
    const entry = entries[entryIndex];
    if (canonicalRoleKey(entry?.speaker) === targetRole) {
      return entryIndex;
    }
  }
  return -1;
}

export function sectionIndexByPartId(sections: Section[]): Map<number | null, number> {
  const mapping = new Map<number | null, number>();
  for (let index = 0; index < sections.length; index += 1) {
    mapping.set(sections[index].partId, index);
  }
  return mapping;
}

export function previousSectionStartIndex(
  entries: PlayPageEntry[],
  index: number,
  sectionIndexMap: Map<number | null, number>,
  sections: Section[],
): number {
  if (index < 0 || index >= entries.length) {
    return -1;
  }
  const currentPartId = entries[index]?.partId ?? null;
  const currentSectionIndex = sectionIndexMap.get(currentPartId);
  if (currentSectionIndex === undefined) {
    return -1;
  }

  const currentSectionStart = sectionStartIndexForPartId(entries, currentPartId);
  if (currentSectionStart < 0) {
    return -1;
  }
  if (index > currentSectionStart) {
    return currentSectionStart;
  }
  if (currentSectionIndex <= 0) {
    return -1;
  }

  const targetPartId = sections[currentSectionIndex - 1]?.partId ?? null;
  return sectionStartIndexForPartId(entries, targetPartId);
}

export function nextSectionStartIndex(
  entries: PlayPageEntry[],
  index: number,
  sectionIndexMap: Map<number | null, number>,
  sections: Section[],
): number {
  if (index < 0 || index >= entries.length) {
    return -1;
  }
  const currentPartId = entries[index]?.partId ?? null;
  const currentSectionIndex = sectionIndexMap.get(currentPartId);
  if (currentSectionIndex === undefined) {
    return -1;
  }
  const currentSectionStart = sectionStartIndexForPartId(entries, currentPartId);
  if (currentSectionStart < 0) {
    return -1;
  }
  if (index < currentSectionStart) {
    return currentSectionStart;
  }
  if (currentSectionIndex >= sections.length - 1) {
    return -1;
  }
  const targetPartId = sections[currentSectionIndex + 1]?.partId ?? null;
  return sectionStartIndexForPartId(entries, targetPartId);
}

export function sectionWindowForIndex(
  entries: PlayPageEntry[],
  index: number,
  sectionIndexMap: Map<number | null, number>,
  sections: Section[],
): SectionWindow {
  if (entries.length === 0) {
    return { start: 0, end: 0, label: "Section" };
  }

  if (index < 0 || index >= entries.length) {
    return { start: 0, end: entries.length, label: sections[0]?.title ?? "Section" };
  }

  const currentPartId = entries[index]?.partId ?? null;
  const currentSectionIndex = sectionIndexMap.get(currentPartId);
  if (currentSectionIndex === undefined) {
    return { start: 0, end: entries.length, label: "Section" };
  }

  const currentSectionStart = sectionStartIndexForPartId(entries, currentPartId);
  if (currentSectionStart < 0) {
    return { start: 0, end: entries.length, label: "Section" };
  }

  let endIndex = entries.length;
  for (let sectionOffset = currentSectionIndex + 1; sectionOffset < sections.length; sectionOffset += 1) {
    const nextPartId = sections[sectionOffset]?.partId ?? null;
    const nextSectionStart = sectionStartIndexForPartId(entries, nextPartId);
    if (nextSectionStart > currentSectionStart) {
      endIndex = nextSectionStart;
      break;
    }
  }

  const sectionTitle = sections[currentSectionIndex]?.title?.trim();
  return {
    start: currentSectionStart,
    end: endIndex,
    label: sectionTitle && sectionTitle.length > 0 ? sectionTitle : "Section",
  };
}

function sectionStartIndexForPartId(entries: PlayPageEntry[], targetPartId: number | null): number {
  for (let entryIndex = 0; entryIndex < entries.length; entryIndex += 1) {
    if (entries[entryIndex]?.partId === targetPartId) {
      return entryIndex;
    }
  }
  return -1;
}

function canonicalRoleKey(rawSpeaker?: string): string {
  return (rawSpeaker ?? "").trim().replace(/^_+/, "").toLowerCase();
}
