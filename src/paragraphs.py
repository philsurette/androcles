#!/usr/bin/env python3
from pathlib import Path

from paths import ROOT, DEFAULT_PLAY, PARAGRAPHS_PATH as OUT_PATH


def collapse_to_paragraphs(text: str) -> list[str]:
    """
    Join consecutive non-empty lines with spaces and use blank lines as
    paragraph boundaries, without emitting blank lines.
    """
    output: list[str] = []
    buffer: list[str] = []

    for raw_line in text.splitlines():
        # Treat any whitespace-only line as a boundary.
        if raw_line.strip():
            buffer.append(raw_line.strip())
        else:
            if buffer:
                output.append(" ".join(buffer))
                buffer.clear()

    if buffer:
        output.append(" ".join(buffer))

    return output


def main() -> None:
    (ROOT.parent / "build").mkdir(parents=True, exist_ok=True)
    text = DEFAULT_PLAY.read_text(encoding="utf-8-sig")
    paragraphs = collapse_to_paragraphs(text)
    if paragraphs:
        OUT_PATH.write_text("\n".join(paragraphs) + "\n", encoding="utf-8")
    else:
        OUT_PATH.write_text("", encoding="utf-8")


if __name__ == "__main__":
    main()
