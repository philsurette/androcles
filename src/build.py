#!/usr/bin/env python3
"""Build text artifacts, split audio segments, verify splits, and check recordings."""
from pathlib import Path
import logging
from datetime import datetime

import typer

import paragraphs as pg
import blocks
import roles
import narration
from role_splitter import process_role
from narrator_splitter import split_narration
from segment_verifier import verify_segments
from recording_checker import summarize as summarize_recordings
from timings_xlsx import generate_xlsx
from play_builder import build_part_audio
from paths import RECORDINGS_DIR, AUDIO_OUT_DIR, BUILD_DIR


app = typer.Typer(add_completion=False)


def setup_logging() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    log_path = BUILD_DIR / "build.log"
    if log_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_path.rename(BUILD_DIR / f"build-{timestamp}.log")

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)


def build_paragraphs() -> None:
    text = pg.DEFAULT_PLAY.read_text(encoding="utf-8-sig")
    paragraphs = pg.collapse_to_paragraphs(text)
    if paragraphs:
        pg.OUT_PATH.write_text("\n".join(paragraphs) + "\n", encoding="utf-8")
    else:
        pg.OUT_PATH.write_text("", encoding="utf-8")


def build_blocks() -> None:
    blocks.prepare_output_dirs()
    _, block_map, index = blocks.parse()
    blocks.write_blocks(block_map)
    blocks.write_index(index)
    roles.build_roles()
    narration.build_narration()


def split_roles(
    role_filter: str | None = None,
    part_filter: str | None = None,
    min_silence_ms: int = 1700,
    silence_thresh: int = -45,
    chunk_size: int = 1,
) -> None:
    for rec in RECORDINGS_DIR.glob("*.wav"):
        if rec.name.startswith("_"):
            continue
        role = rec.stem
        if role_filter and role_filter != role:
            continue
        process_role(
            role,
            min_silence_ms=min_silence_ms,
            silence_thresh=silence_thresh,
            part_filter=part_filter,
            chunk_size=chunk_size,
        )


def split_narrator(
    part_filter: str | None = None, min_silence_ms: int = 1700, silence_thresh: int = -45, chunk_size: int = 1
) -> None:
    split_narration(part_filter=part_filter, min_silence_ms=min_silence_ms, silence_thresh=silence_thresh, chunk_size=chunk_size)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    setup_logging()
    if ctx.invoked_subcommand is None:
        build_paragraphs()
        build_blocks()


@app.command()
def segments(
    role: str = typer.Option(None, help="Limit to a specific role"),
    part: str = typer.Option(None, help="Limit to a specific part id (use '_' for no-part narration entries)"),
    silence_thresh: int = typer.Option(-60, help="Silence threshold dBFS for splitting"),
    separator_len_ms: int = typer.Option(1700, "--separator-length-ms", help="Minimum silence length (ms) to split on"),
    chunk_size: int = typer.Option(50, help="Chunk size (ms) for silence detection"),
) -> None:
    setup_logging()
    build_paragraphs()
    build_blocks()
    if role is None:
        split_roles(part_filter=part, min_silence_ms=separator_len_ms, silence_thresh=silence_thresh, chunk_size=chunk_size)
        split_narrator(part_filter=part, min_silence_ms=separator_len_ms, silence_thresh=silence_thresh, chunk_size=chunk_size)
    elif role == "_NARRATOR":
        split_narrator(part_filter=part, min_silence_ms=separator_len_ms, silence_thresh=silence_thresh, chunk_size=chunk_size)
    else:
        split_roles(
            role_filter=role, part_filter=part, min_silence_ms=separator_len_ms, silence_thresh=silence_thresh, chunk_size=chunk_size
        )


@app.command()
def verify(
    tol_low: float = typer.Option(0.5, help="Lower bound ratio of actual/expected"),
    tol_high: float = typer.Option(2.0, help="Upper bound ratio of actual/expected"),
) -> None:
    setup_logging()
    verify_segments(tol_low, tol_high)


@app.command()
def check_recording() -> None:
    setup_logging()
    timings_path = AUDIO_OUT_DIR / "timings.csv"
    if not timings_path.exists():
        typer.echo(f"{timings_path} not found; run verify first.")
        raise typer.Exit(code=1)
    for line in summarize_recordings(timings_path):
        typer.echo(line)


@app.command("generate-timings")
def generate_timings() -> None:
    setup_logging()
    generate_xlsx()


@app.command()
def audioplay(
    part: str = typer.Option(..., help="Part number to assemble, or '_' for preamble (no part)"),
    segment_spacing_ms: int = typer.Option(1000, help="Silence (ms) to insert between segments"),
    callouts: bool = typer.Option(False, help="Prepend each role line with its callout audio"),
    callout_spacing_ms: int = typer.Option(300, help="Silence (ms) between callout and line"),
    minimal_callouts: bool = typer.Option(False, help="Reduce callouts during alternating two-person dialogue"),
) -> None:
    setup_logging()
    build_paragraphs()
    build_blocks()
    if part == "_":
        part_filter = None
    else:
        try:
            part_filter = int(part)
        except ValueError:
            raise typer.BadParameter("Part must be an integer or '_'")
    build_part_audio(
        part_filter,
        spacing_ms=segment_spacing_ms,
        include_callouts=callouts,
        callout_spacing_ms=callout_spacing_ms,
        minimal_callouts=minimal_callouts,
    )


if __name__ == "__main__":
    app()
