#!/usr/bin/env python3
"""Build text artifacts, split audio segments, verify splits, and check recordings."""
from pathlib import Path
import logging
import sys
import shlex
from datetime import datetime

import typer

from play_splitter import PlaySplitter
from recording_checker import summarize as summarize_recordings
from timings_xlsx import generate_xlsx
from play_builder import PlayBuilder, list_parts, compute_output_path
from play_text import PlayTextParser
from markdown_renderer import PlayMarkdownWriter,  RoleMarkdownWriter
from loudnorm.normalizer import Normalizer
from cue_builder import CueBuilder
from paths import AUDIO_OUT_DIR, BUILD_DIR, LOGS_DIR, SEGMENTS_DIR
from play_plan_builder import PlayPlanBuilder
from segment_verifier import SegmentVerifier


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


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    setup_logging()
    if ctx.invoked_subcommand is None:
        run_segments()
        run_text()
        run_audioplay()

@app.command()
def text() -> None:
    """Build markdown artifacts."""
    setup_logging()
    run_text()


@app.command()
def write_play(
    line_no_prefix: bool = typer.Option(True, "--line_no_prefix/--no_line_no_prefix", help="prepend line numbers to each block"),
) -> None:
    """Write build/text/<play>.md"""
    setup_logging()
    run_write_play(line_no_prefix)

@app.command()
def write_roles(
    line_no_prefix: bool = typer.Option(True, "--line_no_prefix/--no_line_no_prefix", help="prepend line numbers to each block"),
) -> None:
    """Write build/text/<role>.md - all blocks for each role"""
    setup_logging()
    run_write_roles(line_no_prefix)

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
) -> None:
    setup_logging()
    run_segments(
        role=role,
        part=part,
        silence_thresh=silence_thresh,
        separator_len_ms=separator_len_ms,
        chunk_size=chunk_size,
        verbose=verbose,
        chunk_exports=chunk_exports,
        chunk_export_size=chunk_export_size,
    )

@app.command()
def verify(
    too_short: float = typer.Option(0.5, help="Lower bound ratio of actual/expected"),
    too_long: float = typer.Option(2.0, help="Upper bound ratio of actual/expected"),
) -> None:
    setup_logging()
    _run_verify(too_short, too_long)


def _run_verify(too_short: float = 0.5, too_long: float = 2.0) -> None:
    play = PlayTextParser().parse()
    builder = PlayPlanBuilder(play_text=play)
    plan, _ = builder.build_audio_plan(parts=builder.list_parts())
    verifier = SegmentVerifier(plan=plan, too_short=too_short, too_long=too_long, play_text=play)
    verifier.verify_segments()


@app.command()
def check_recording() -> None:
    setup_logging()
    run_check_recording()


@app.command("generate-timings")
def generate_timings() -> None:
    setup_logging()
    run_generate_timings()


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
    run_audioplay(
        part=part,
        segment_spacing_ms=segment_spacing_ms,
        callouts=callouts,
        callout_spacing_ms=callout_spacing_ms,
        minimal_callouts=minimal_callouts,
        captions=captions,
        generate_audio=generate_audio,
        librivox=librivox,
        audio_format=audio_format,
        normalize_output=normalize_output,
    )


@app.command()
def normalize(
    src: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True),
) -> None:
    """
    Normalize an audio file using ffmpeg loudnorm. Writes to a sibling 'normalized' folder.
    """
    setup_logging()
    result = run_normalize(src)
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
    run_cues(
        role=role,
        response_delay_ms=response_delay_ms,
        max_cue_size_ms=max_cue_size_ms,
        include_prompts=include_prompts,
        callout_spacing_ms=callout_spacing_ms,
    )


# Helper functions (non-Typer) -----------------------------------------------

def run_text(line_no_prefix: bool = True) -> None:
    run_write_play(line_no_prefix)
    run_write_roles(line_no_prefix)


def run_write_play(line_no_prefix: bool = True):
    play = PlayTextParser().parse()
    writer = PlayMarkdownWriter(play, prefix_line_nos=line_no_prefix)
    path = writer.to_markdown()
    logging.info("✅ wrote %s", path)
    return path


def run_write_roles(line_no_prefix: bool = True):
    play = PlayTextParser().parse()
    paths = []
    for role in play.roles:
        writer = RoleMarkdownWriter(role, prefix_line_nos=line_no_prefix)
        path = writer.to_markdown()
        paths.append(path)
        logging.debug("✅ wrote %s", path)
    if paths:
        logging.info("✅ created .md files in %s for %s", paths[0].parent, ",".join([r.name for r in play.roles]))
    return paths


def run_segments(
    *,
    role: str | None = None,
    part: str | None = None,
    silence_thresh: int = -60,
    separator_len_ms: int = 1700,
    chunk_size: int = 50,
    verbose: bool = False,
    chunk_exports: bool = True,
    chunk_export_size: int = 25,
):
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
    return splitter.split_all(part_filter=part, role_filter=role)


def run_check_recording():
    timings_path = AUDIO_OUT_DIR / "timings.csv"
    if not timings_path.exists():
        typer.echo(f"{timings_path} not found; run verify first.")
        raise typer.Exit(code=1)
    for line in summarize_recordings(timings_path):
        typer.echo(line)


def run_generate_timings():
    generate_xlsx()


def run_audioplay(
    *,
    part: str | None = None,
    segment_spacing_ms: int = 1000,
    callouts: bool = True,
    callout_spacing_ms: int = 300,
    minimal_callouts: bool = True,
    captions: bool = True,
    generate_audio: bool = True,
    librivox: bool = False,
    audio_format: str = "mp4",
    normalize_output: bool = True,
):
    if audio_format not in ("mp4", "mp3", "wav"):
        raise typer.BadParameter("audio-format must be one of: mp4, mp3, wav")
    if part == "_":
        parts = [None]
        part_val = None
    elif part is None:
        parts = list_parts()
        part_val = None
    else:
        try:
            part_val = int(part)
            parts = [part_val]
        except ValueError:
            raise typer.BadParameter("Part must be an integer or '_'")

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
    out_paths = builder.build_audio(parts=parts, part=part_val)
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
    return out_paths


def run_normalize(src: Path):
    normalizer = Normalizer()
    src_parent = src.parent
    out_dir = src_parent / "normalized"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / src.name
    return normalizer.normalize(str(src), str(out_path))


def run_cues(
    *,
    role: str | None = None,
    response_delay_ms: int = 2000,
    max_cue_size_ms: int = 5000,
    include_prompts: bool = True,
    callout_spacing_ms: int = 300,
):
    play_text = PlayTextParser().parse()
    builder = CueBuilder(
        play_text,
        response_delay_ms=response_delay_ms,
        max_cue_size_ms=max_cue_size_ms,
        include_prompts=include_prompts,
        callout_spacing_ms=callout_spacing_ms,
    )
    roles = [role] if role else [r.name for r in play_text.roles] + ["_NARRATOR"]
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
