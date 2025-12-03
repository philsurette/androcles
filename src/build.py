#!/usr/bin/env python3
"""Build text artifacts, split audio segments, verify splits, and check recordings."""
from pathlib import Path
import logging
import sys
import shlex
from datetime import datetime

import typer

import paragraphs as pg
import blocks
import roles
import narration
from play_splitter import PlaySplitter
from segment_verifier import verify_segments
from recording_checker import summarize as summarize_recordings
from timings_xlsx import generate_xlsx
from play_builder import PlayBuilder, list_parts, compute_output_path
from play_text import PlayTextParser
from markdown_renderer import PlayMarkdownWriter,  RoleMarkdownWriter
from loudnorm.normalizer import Normalizer
from cue_builder import CueBuilder
from paths import RECORDINGS_DIR, AUDIO_OUT_DIR, BUILD_DIR, LOGS_DIR, SEGMENTS_DIR


app = typer.Typer(add_completion=False)


def setup_logging() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / "build.log"
    if log_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_path.rename(LOGS_DIR / f"build-{timestamp}.log")

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


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    setup_logging()
    if ctx.invoked_subcommand is None:
        build_paragraphs()
        build_blocks()


@app.command()
def text() -> None:
    """Build text artifacts (paragraphs, blocks, roles, narration)."""
    setup_logging()
    build_paragraphs()
    build_blocks()


@app.command()
def write_play(
    line_no_prefix: bool = typer.Option(True, "--line_no_prefix/--no_line_no_prefix", help="prepend line numbers to each block"),
) -> None:
    """Write build/text/<play>.md"""
    setup_logging()
    play = PlayTextParser().parse()
    writer = PlayMarkdownWriter(play, prefix_line_nos=line_no_prefix)
    path = writer.to_markdown()
    logging.info("✅ wrote %s", path)

@app.command()
def write_roles(
    line_no_prefix: bool = typer.Option(True, "--line_no_prefix/--no_line_no_prefix", help="prepend line numbers to each block"),
) -> None:
    """Write build/text/<role>.md - all blocks for each role"""
    setup_logging()
    play = PlayTextParser().parse()
    for role in play.roles:
        writer = RoleMarkdownWriter(role, prefix_line_nos=line_no_prefix)
        path = writer.to_markdown()
        logging.info("✅ wrote %s", path)

@app.command()
def segments(
    role: str = typer.Option(None, help="Limit to a specific role"),
    part: str = typer.Option(None, help="Limit to a specific part id (use '_' for no-part narration entries)"),
    silence_thresh: int = typer.Option(-60, help="Silence threshold dBFS for splitting"),
    separator_len_ms: int = typer.Option(1700, "--separator-length-ms", help="Minimum silence length (ms) to split on"),
    chunk_size: int = typer.Option(50, help="Chunk size (ms) for silence detection"),
    verbose: bool = typer.Option(False, "--verbose", help="Log ffmpeg commands used for splitting"),
    chunk_exports: bool = typer.Option(True, "--chunk-exports/--no-chunk-exports", help="Export in batches"),
    chunk_export_size: int = typer.Option(25, "--chunk-export-size", help="Batch size when chunking exports"),
    use_silence_window: bool = typer.Option(
        False, "--use-silence-window/--no-use-silence-window", help="Windowed silence detection"
    ),
    silence_window_size_seconds: int = typer.Option(300, "--silence-window-size-seconds", help="Window size in seconds"),
) -> None:
    setup_logging()
    build_paragraphs()
    build_blocks()
    play_text = PlayTextParser().parse()
    splitter = PlaySplitter(
        play_text=play_text,
        min_silence_ms=separator_len_ms,
        silence_thresh=silence_thresh,
        chunk_size=chunk_size,
        verbose=verbose,
        chunk_exports=chunk_exports,
        chunk_export_size=chunk_export_size,
    )
    splitter.split_all(part_filter=part, role_filter=role)


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
    part: str = typer.Option(None, help="Part number to assemble, '_' for preamble, omit for all parts"),
    segment_spacing_ms: int = typer.Option(1000, help="Silence (ms) to insert between segments"),
    callouts: bool = typer.Option(True, help="Prepend each role line with its callout audio"),
    callout_spacing_ms: int = typer.Option(300, help="Silence (ms) between callout and line"),
    minimal_callouts: bool = typer.Option(True, help="Reduce callouts during alternating two-person dialogue"),
    captions: bool = typer.Option(True, help="Generate captions (WebVTT) and mux into mp4 when possible"),
    generate_audio: bool = typer.Option(True, help="Write rendered audio (disable to only emit audio_plan.txt)"),
    librivox: bool = typer.Option(False, help="Generate Librivox-style mp3s (one per part, no prelude)"),
    audio_format: str = typer.Option("mp4", help="Output format: mp4 (default), mp3, or wav"),
    normalize_output: bool = typer.Option(True, help="Normalize the generated audioplay"),
) -> None:
    setup_logging()
    build_paragraphs()
    build_blocks()
    if audio_format not in ("mp4", "mp3", "wav"):
        raise typer.BadParameter("audio-format must be one of: mp4, mp3, wav")
    parts = []
    if part is None:
        parts = list_parts()
    else:
        if part == "_":
            parts = [None]
            part = None
        else:
            try:
                part = int(part)
                parts = [part]
            except ValueError:
                raise typer.BadParameter("Part must be an integer or '_'")
    if audio_format not in ("mp4", "mp3", "wav"):
        raise typer.BadParameter("audio-format must be one of: mp4, mp3, wav")
    builder = PlayBuilder(
        spacing_ms=segment_spacing_ms,
        include_callouts=callouts,
        callout_spacing_ms=callout_spacing_ms,
        minimal_callouts=minimal_callouts,
        audio_format=audio_format,
        part_gap_ms=2000 if len(parts) > 1 else 0,
        generate_audio=generate_audio,
        generate_captions=captions,
        librivox=librivox,
    )
    out_paths = builder.build_audio(parts=parts, part=part)
    if normalize_output and generate_audio:
        normalizer = Normalizer()
        for out_path in out_paths:
            target_dir = out_path.parent / "normalized"
            target_dir.mkdir(parents=True, exist_ok=True)
            norm_path = target_dir / out_path.name
            logging.info("Normalizing audioplay to %s", norm_path)
            normalizer.normalize(str(out_path), str(norm_path))
    elif normalize_output and not generate_audio:
        logging.info("Skipping normalization because audio rendering was skipped.")


@app.command()
def normalize(
    src: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True),
) -> None:
    """
    Normalize an audio file using ffmpeg loudnorm. Writes to a sibling 'normalized' folder.
    """
    setup_logging()
    normalizer = Normalizer()
    src_parent = src.parent
    out_dir = src_parent / "normalized"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / src.name
    result = normalizer.normalize(str(src), str(out_path))
    typer.echo(result.render())


@app.command()
def cues(
    role: str = typer.Option(None, help="Role to build cues for; default builds all roles"),
    response_delay_ms: int = typer.Option(2000, help="Silence (ms) between cue and response"),
    max_cue_size_ms: int = typer.Option(5000, help="Max cue length before cropping (ms)"),
    include_prompts: bool = typer.Option(True, help="Include preceding prompts; disables if set false"),
    callout_spacing_ms: int = typer.Option(300, help="Silence (ms) between prompt callout and prompt"),
) -> None:
    setup_logging()
    build_paragraphs()
    build_blocks()
    play_text = PlayTextParser().parse()
    builder = CueBuilder(
        play_text,
        response_delay_ms=response_delay_ms,
        max_cue_size_ms=max_cue_size_ms,
        include_prompts=include_prompts,
        callout_spacing_ms=callout_spacing_ms,
    )
    roles = []
    if role:
        roles = [role]
    else:
        roles = [p.name for p in SEGMENTS_DIR.iterdir() if p.is_dir() and not p.name.startswith("_")]
    for r in roles:
        builder.build_cues(r)


# if __name__ == "__main__":
#     app()

if __name__ == "__main__":
    if len(sys.argv) == 2:
        # If only one argument string is passed (e.g., from VSCode or manual entry)
        preprocessed_args = shlex.split(sys.argv[1])
        sys.argv = [sys.argv[0]] + preprocessed_args
    app()
