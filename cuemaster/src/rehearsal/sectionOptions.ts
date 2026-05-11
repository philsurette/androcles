import type { Playbook } from "../domain/playbook";
import type { Role } from "../domain/role";

export type RoleSectionOption = {
  id: string;
  partId: number | null;
  title: string;
  startLineId: string;
  lineCount: number;
};

export function sectionOptionsForRole(playbook: Playbook, role: Role): RoleSectionOption[] {
  const linesByPartId = new Map<number | null, Role["lines"]>();
  for (const line of role.lines) {
    const lines = linesByPartId.get(line.partId) ?? [];
    lines.push(line);
    linesByPartId.set(line.partId, lines);
  }

  const options: RoleSectionOption[] = [];
  for (const section of playbook.sections) {
    const lines = linesByPartId.get(section.partId) ?? [];
    if (lines.length === 0) {
      continue;
    }
    options.push({
      id: section.id,
      partId: section.partId,
      title: section.title,
      startLineId: lines[0].id,
      lineCount: lines.length
    });
    linesByPartId.delete(section.partId);
  }

  for (const [partId, lines] of linesByPartId) {
    options.push({
      id: partId === null ? "play" : `part-${partId}`,
      partId,
      title: partId === null ? "Play" : `Part ${partId + 1}`,
      startLineId: lines[0].id,
      lineCount: lines.length
    });
  }

  return options;
}
