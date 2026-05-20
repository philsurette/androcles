export const practiceFlows = ["manual", "listen", "try", "try_then_check"] as const;

export type PracticeFlow = (typeof practiceFlows)[number];

export const practiceFlowLabels: Record<PracticeFlow, string> = {
  manual: "Manual",
  listen: "Listen",
  try: "Try",
  try_then_check: "Try + Hear Line"
};

export function isPracticeFlow(value: string): value is PracticeFlow {
  return practiceFlows.includes(value as PracticeFlow);
}
