import type { ContextBlock as ContextBlockModel } from "../../domain/context";

export function ContextBlock({ block }: { block: ContextBlockModel }) {
  return <aside className={`context context-${block.kind}`}>{block.text}</aside>;
}
