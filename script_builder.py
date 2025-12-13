from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import typer


app = typer.Typer(add_completion=False)


@dataclass
class Chapter:
    number: int
    title: str
    blocks: List[str]


CHAPTER_PATTERN = re.compile(r"^##\s+(\d+)\b")


def join_block(lines: Iterable[str]) -> str:
    """Collapse a block of text lines into a single line."""
    return " ".join(line.strip() for line in lines if line.strip())


def parse_chapters(src_path: Path) -> list[Chapter]:
    chapters: list[Chapter] = []
    current_title: str | None = None
    current_number: int | None = None
    blocks: list[str] = []
    block_lines: list[str] = []
    started = False

    for raw_line in src_path.read_text(encoding="utf-8").splitlines():
        match = CHAPTER_PATTERN.match(raw_line)
        if match:
            # Finalize the previous chapter, if any.
            if current_title is not None and current_number is not None:
                if block_lines:
                    blocks.append(join_block(block_lines))
                    block_lines = []
                chapters.append(Chapter(current_number, current_title, blocks))
                blocks = []
            started = True
            current_title = raw_line.rstrip()
            current_number = int(match.group(1))
            block_lines = []
            continue

        if not started:
            # Ignore everything before the first chapter marker.
            continue

        if raw_line.strip():
            block_lines.append(raw_line)
        else:
            if block_lines:
                blocks.append(join_block(block_lines))
                block_lines = []

    # Flush the final chapter.
    if current_title is not None and current_number is not None:
        if block_lines:
            blocks.append(join_block(block_lines))
        chapters.append(Chapter(current_number, current_title, blocks))

    return chapters


def write_chapter_files(chapters: list[Chapter], output_dir: Path, input_stem: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written_files: list[Path] = []

    for chapter in chapters:
        filename = f"{chapter.number:02d}-{input_stem}.txt"
        dest = output_dir / filename

        lines: list[str] = [chapter.title]
        if chapter.blocks:
            lines.append("")
            for idx, block in enumerate(chapter.blocks):
                lines.append(block)
                if idx < len(chapter.blocks) - 1:
                    lines.append("")

        dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written_files.append(dest)

    return written_files


def zip_chapters(zip_path: Path, chapter_files: list[Path]) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for chapter_file in chapter_files:
            zf.write(chapter_file, arcname=chapter_file.name)


@app.command()
def build(
    input_file: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Source text file containing chapters",
    )
) -> None:
    input_stem = input_file.stem
    chapters = parse_chapters(input_file)

    if not chapters:
        typer.echo("No chapters found in the provided file.", err=True)
        raise typer.Exit(code=1)

    output_dir = Path("build") / input_stem
    written_files = write_chapter_files(chapters, output_dir, input_stem)

    zip_path = output_dir / f"{input_stem}.zip"
    zip_chapters(zip_path, written_files)

    typer.echo(f"Wrote {len(written_files)} chapters to {output_dir}")
    typer.echo(f"Created zip archive at {zip_path}")


if __name__ == "__main__":
    app()
