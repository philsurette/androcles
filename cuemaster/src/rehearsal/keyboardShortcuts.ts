export type RehearsalShortcut = "repeat-cue" | "next" | "previous" | "hear-line" | "stop";

export function shortcutForKey(event: Pick<KeyboardEvent, "key" | "target">): RehearsalShortcut | null {
  if (isEditableTarget(event.target)) {
    return null;
  }

  switch (event.key) {
    case " ":
    case "Spacebar":
    case "r":
    case "R":
      return "repeat-cue";
    case "ArrowRight":
      return "next";
    case "ArrowLeft":
      return "previous";
    case "l":
    case "L":
      return "hear-line";
    case "Escape":
      return "stop";
    default:
      return null;
  }
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }
  return (
    target.isContentEditable ||
    target.tagName === "INPUT" ||
    target.tagName === "TEXTAREA" ||
    target.tagName === "SELECT"
  );
}
