import type { Playbook, PlaybookLine } from "../domain/playbook";
import type { PracticeFlow } from "../practice/practiceFlow";
import { buildPracticeFlowSteps } from "../practice/practiceFlowRunner";

export type PlaybackStep =
  | { kind: "audio"; label: string; audioPath: string; durationMs: number }
  | { kind: "wait"; label: string; durationMs: number }
  | { kind: "advance"; label: string };

export class RoleRehearsalSequenceBuilder {
  build(line: PlaybookLine, flow: PracticeFlow, linePace: number): PlaybackStep[] {
    const responseDurationMs = line.responseSegments.reduce((total, segment) => total + segment.durationMs, 0);
    const steps = buildPracticeFlowSteps({
      flow,
      lineId: line.id,
      responseDurationMs,
      linePace,
      responsePaddingMs: 750
    });

    return steps.flatMap((step): PlaybackStep[] => {
      if (step.kind === "cue") {
        return [
          {
            kind: "audio",
            label: `Cue: ${line.cue.speaker}`,
            audioPath: line.cue.audioPath,
            durationMs: line.cue.durationMs
          }
        ];
      }
      if (step.kind === "silent-response") {
        return [{ kind: "wait", label: "Your turn", durationMs: step.durationMs }];
      }
      if (step.kind === "reference") {
        return line.responseSegments.map((segment) => ({
          kind: "audio",
          label: "Hear Line",
          audioPath: segment.audioPath,
          durationMs: Math.round(segment.durationMs / linePace)
        }));
      }
      return [{ kind: "advance", label: "Next line" }];
    });
  }
}

export class WholePlaySequenceBuilder {
  build(playbook: Playbook): WholePlayItem[] {
    const entries = [
      ...playbook.context
        .filter((block) => block.kind !== "blocking")
        .map((block) => ({
          id: block.id,
          partId: block.partId,
          blockId: block.blockId,
          speaker: block.speaker,
          text: block.text,
          audioPath: block.audioPath,
          durationMs: block.durationMs,
          kind: block.kind
        })),
      ...playbook.roles.flatMap((role) =>
        role.lines.flatMap((line) =>
          line.responseSegments.map((segment) => ({
            id: line.id,
            partId: line.partId,
            blockId: line.blockId,
            speaker: line.speaker,
            text: segment.text,
            audioPath: segment.audioPath,
            durationMs: segment.durationMs,
            kind: "speech"
          }))
        )
      )
    ];

    return entries
      .sort((left, right) => this.compareEntries(left, right))
      .map((entry) => ({
        id: entry.id,
        speaker: entry.speaker,
        text: entry.text,
        kind: entry.kind,
        audioPath: entry.audioPath,
        durationMs: entry.durationMs ?? 0,
        blocking: playbook.context
          .filter((block) => block.kind === "blocking" && block.id.startsWith(`${entry.id}:`))
          .map((block) => ({ id: block.id, text: block.text }))
      }));
  }

  private compareEntries(left: SortablePlayEntry, right: SortablePlayEntry): number {
    const part = (left.partId ?? -1) - (right.partId ?? -1);
    if (part !== 0) {
      return part;
    }
    return this.blockSortKey(left.blockId).localeCompare(this.blockSortKey(right.blockId), undefined, { numeric: true });
  }

  private blockSortKey(blockId: string): string {
    return blockId.replaceAll(".", "-");
  }
}

export type WholePlayItem = {
  id: string;
  speaker: string;
  text: string;
  kind: string;
  audioPath?: string;
  durationMs: number;
  blocking: Array<{ id: string; text: string }>;
};

type SortablePlayEntry = {
  id: string;
  partId: number | null;
  blockId: string;
  speaker: string;
  text: string;
  audioPath?: string;
  durationMs?: number;
  kind: string;
};
