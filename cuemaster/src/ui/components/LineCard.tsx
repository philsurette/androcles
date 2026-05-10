import type { Line } from "../../domain/line";

export function LineCard({ line }: { line: Line }) {
  return <article className="card">{line.responseText}</article>;
}
