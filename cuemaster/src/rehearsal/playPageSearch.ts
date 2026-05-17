import type { Line } from "../domain/line";

export type SearchablePlayPageEntry = {
  type: "line" | "context";
  id: string;
  speaker: string;
  text: string;
  line?: Pick<Line, "directions">;
};

export function entryMatchesSearchQuery(entry: SearchablePlayPageEntry, query: string, title: string): boolean {
  if (query.length === 0) {
    return false;
  }
  const looksLikeId = isLikelyIdQuery(query);
  if (looksLikeId) {
    return entryTokensForSearch(entry, title).some((token) => token === query);
  }
  const haystack = entrySearchHaystack(entry, title);
  return haystack.includes(query);
}

export function entrySearchHaystack(entry: SearchablePlayPageEntry, title: string): string {
  const searchableParts: string[] = [title, entry.id, entry.speaker, entry.text];
  if (entry.type === "line" && entry.line) {
    for (const direction of entry.line.directions) {
      searchableParts.push(direction.text);
    }
  }
  return searchableParts.join(" ").toLowerCase();
}

export function isLikelyIdQuery(query: string): boolean {
  return /^[a-z0-9]+-[0-9]+(?:\.[0-9]+)?$/.test(query) || /^[a-z0-9]+-[a-z0-9]+$/.test(query);
}

export function entryTokensForSearch(entry: SearchablePlayPageEntry, title: string): string[] {
  const searchableParts: string[] = [title, entry.id, entry.speaker, entry.text];
  if (entry.type === "line" && entry.line) {
    for (const direction of entry.line.directions) {
      searchableParts.push(direction.text);
    }
  }
  return searchableParts
    .flatMap((part) => part
      .toLowerCase()
      .split(/[^a-z0-9-]+/)
      .map((token) => token.trim())
      .filter((token) => token.length > 0));
}
