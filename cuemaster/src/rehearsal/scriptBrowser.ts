import type { Line } from "../domain/line";
import type { Section } from "../domain/section";

export type ScriptBrowserSection = {
  id: string;
  title: string;
  lines: Line[];
};

export function scriptBrowserSections(lines: Line[], playbookSections: Section[] = []): ScriptBrowserSection[] {
  const sections = new Map<string, ScriptBrowserSection>();
  const titlesByPartId = new Map(playbookSections.map((section) => [section.partId, section.title]));

  for (const line of lines) {
    const sectionId = line.partId === null ? "play" : `part-${line.partId}`;
    const section = sections.get(sectionId) ?? {
      id: sectionId,
      title: titlesByPartId.get(line.partId) ?? (line.partId === null ? "Play" : `Part ${line.partId + 1}`),
      lines: []
    };
    section.lines.push(line);
    sections.set(sectionId, section);
  }

  return Array.from(sections.values());
}
