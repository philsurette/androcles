import type { PracticeFlow } from "./practiceFlow";

export type PracticeFlowStep =
  | { kind: "cue"; lineId: string }
  | { kind: "silent-response"; lineId: string; durationMs: number }
  | { kind: "reference"; lineId: string }
  | { kind: "advance"; lineId: string };

export type BuildPracticeFlowStepsInput = {
  flow: PracticeFlow;
  lineId: string;
  responseDurationMs: number;
  linePace: number;
  responsePaddingMs: number;
};

export function buildPracticeFlowSteps({
  flow,
  lineId,
  responseDurationMs,
  linePace,
  responsePaddingMs
}: BuildPracticeFlowStepsInput): PracticeFlowStep[] {
  const cue: PracticeFlowStep = { kind: "cue", lineId };
  const reference: PracticeFlowStep = { kind: "reference", lineId };
  const silentResponse: PracticeFlowStep = {
    kind: "silent-response",
    lineId,
    durationMs: silentResponseDurationMs(responseDurationMs, linePace, responsePaddingMs)
  };
  const advance: PracticeFlowStep = { kind: "advance", lineId };

  switch (flow) {
    case "manual":
      return [cue];
    case "listen":
      return [cue, reference, advance];
    case "try":
      return [cue, silentResponse, advance];
    case "try_then_check":
      return [cue, silentResponse, reference, advance];
  }
}

export function silentResponseDurationMs(
  responseDurationMs: number,
  linePace: number,
  responsePaddingMs: number
): number {
  if (linePace <= 0) {
    throw new Error(`Line pace must be greater than zero. Received ${linePace}.`);
  }

  if (responseDurationMs < 0) {
    throw new Error(`Response duration must not be negative. Received ${responseDurationMs}.`);
  }

  if (responsePaddingMs < 0) {
    throw new Error(`Response padding must not be negative. Received ${responsePaddingMs}.`);
  }

  return Math.round(responseDurationMs / linePace + responsePaddingMs);
}
