import type { Line } from "../domain/line";

export type ScriptBrowserSection = {
  id: string;
  title: string;
  lines: Line[];
};

export function scriptBrowserSections(lines: Line[]): ScriptBrowserSection[] {
  const sections = new Map<string, ScriptBrowserSection>();

  for (const line of lines) {
    const sectionId = line.partId === null ? "play" : `part-${line.partId}`;
    const section = sections.get(sectionId) ?? {
      id: sectionId,
      title: line.partId === null ? "Play" : `Part ${line.partId + 1}`,
      lines: []
    };
    section.lines.push(line);
    sections.set(sectionId, section);
  }

  return Array.from(sections.values());
}
