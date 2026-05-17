import type { ContextBlock } from "../domain/context";
import type { Cue } from "../domain/cue";
import type { Line } from "../domain/line";
import type { Playbook } from "../domain/playbook";
import type { BlockingScope } from "../ui/components/LineCard";

export type OutlineMode = "cues" | "lines";

export function outlineSearchText(
  line: Line,
  mode: OutlineMode,
  includeDirections: boolean,
  includeBlocking: boolean,
  blockingScope: BlockingScope,
  playbook: Playbook
): string {
  const parts = [
    line.id,
    outlineSpeaker(line, mode, includeDirections, playbook),
    outlineText(line, mode, includeDirections, playbook)
  ];
  if (mode === "cues") {
    return parts.join(" ");
  }
  if (mode === "lines" && includeDirections) {
    parts.push(...line.directions.map((direction) => direction.text));
  }
  if (mode === "lines" && includeBlocking) {
    parts.push(...visibleBlockingForLine(line, blockingScope).map((blocking) => `${blocking.targets.join(" ")} ${blocking.text}`));
  }
  return parts.join(" ");
}

export function outlineSpeaker(line: Line, mode: OutlineMode, includeDirections: boolean, playbook: Playbook): string {
  if (mode === "cues") {
    return visibleCuesForDisplay([line.cue], false, playbook.context, playbook, line)[0]?.speaker ?? line.cue.speaker;
  }
  if (mode === "lines") {
    return line.speaker;
  }
  return "";
}

export function outlineText(line: Line, mode: OutlineMode, includeDirections: boolean, playbook: Playbook): string {
  if (mode === "lines") {
    return line.responseText;
  }
  return visibleCuesForDisplay([line.cue], false, playbook.context, playbook, line)[0]?.text ?? line.cue.text;
}

export function visibleBlockingForLine(line: Line, blockingScope: BlockingScope) {
  return (line.blocking ?? []).filter(
    (blocking) => blockingScope === "all" || blocking.targets.includes("*") || blocking.targets.includes(line.role)
  );
}

export function visibleCuesForDisplay(
  cues: Cue[],
  includeDirections: boolean,
  context: ContextBlock[] = [],
  playbook?: Playbook,
  currentLine?: Line
): Cue[] {
  if (includeDirections) {
    return cues;
  }
  const contextKindByCueKey = new Map(
    context
      .filter((block) => block.audioPath)
      .map((block) => [cueKey(block.speaker, block.text, block.audioPath ?? ""), block.kind])
  );
  return cues.map((cue) => {
    const kind = cue.kind ?? contextKindByCueKey.get(cueKey(cue.speaker, cue.text, cue.audioPath));
    if (kind === "description" || kind === "direction") {
      return precedingSpeechCue(playbook, currentLine) ?? cue;
    }
    return cue;
  });
}

export function resolveCurrentLineFromEngine(
  roleLines: Line[],
  positionIndex: number,
  fallbackLine: Line | null
): Line | null {
  return roleLines[positionIndex] ?? fallbackLine;
}

function cueKey(speaker: string, text: string, audioPath: string) {
  return `${speaker}\u0000${text}\u0000${audioPath}`;
}

function precedingSpeechCue(playbook: Playbook | undefined, currentLine: Line | undefined): Cue | null {
  if (!playbook || !currentLine) {
    return null;
  }
  const priorLine = playbook.roles
    .flatMap((role) => role.lines)
    .filter((line) => line.responseSegments.length > 0)
    .filter((line) => blockOrder(line.blockId) < blockOrder(currentLine.blockId))
    .sort((left, right) => blockOrder(right.blockId) - blockOrder(left.blockId))[0];
  if (!priorLine) {
    return null;
  }
  return {
    speaker: priorLine.speaker,
    text: priorLine.responseText,
    audioPath: priorLine.responseSegments[0].audioPath,
    durationMs: priorLine.responseSegments.reduce((totalMs, segment) => totalMs + segment.durationMs, 0),
    kind: "speech"
  };
}

function blockOrder(blockId: string): number {
  return blockId
    .split(".")
    .reduce((total, part, index) => total + Number(part) * 1000 ** (3 - index), 0);
}
