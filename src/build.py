#!/usr/bin/env python3
"""Build text artifacts, split audio segments, verify splits, and check recordings."""
from pathlib import Path
import logging
import sys
import shlex
from datetime import datetime

import paths
import typer

from play_splitter import PlaySplitter
from recording_checker import summarize as summarize_recordings
from timings_xlsx import generate_xlsx
from play_builder import PlayBuilder
from play import Play, Part
from play_text_parser import PlayTextParser
from announcer_script_writer import AnnouncerScriptWriter
from play_markdown_writer import PlayMarkdownWriter
from role_markdown_writer import RoleMarkdownWriter
from narrator_markdown_writer import NarratorMarkdownWriter
from callouts_markdown_writer import CalloutsMarkdownWriter
from callout_script_writer import CalloutScriptWriter
from loudnorm.normalizer import Normalizer
from cue_builder import CueBuilder
from play_plan_builder import PlayPlanBuilder
from segment_verifier import SegmentVerifier

from spacing import (
  CALLOUT_SPACING_MS,
  SEGMENT_SPACING_MS
)

app = typer.Typer(add_completion=False)
PLAY_OPTION = typer.Option(
    None,
    "--play",
    "-p",
    help=f"Play directory name under plays/ (default: {paths.DEFAULT_PLAY_NAME})",
)


def setup_logging() -> None:
    paths.BUILD_DIR.mkdir(parents=True, exist_ok=True)
    paths.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = paths.LOGS_DIR / "build.log"
    if log_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_path.rename(paths.LOGS_DIR / f"build-{timestamp}.log")

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
def main(ctx: typer.Context, play: str | None = PLAY_OPTION) -> None:
    play_name = play or paths.DEFAULT_PLAY_NAME
    paths.set_play_name(play_name)
    setup_logging()
    if ctx.invoked_subcommand is None:
        run_segments()
        run_text()
        run_audioplay()

@app.command()
def text(play: str | None = PLAY_OPTION) -> None:
    """Build markdown artifacts."""
    paths.set_play_name(play or paths.PLAY_NAME)
    setup_logging()
    run_text()


@app.command()
def write_play(
    line_no_prefix: bool = typer.Option(True, "--line_no_prefix/--no_line_no_prefix", help="prepend line numbers to each block"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Write build/text/<play>.md"""
    paths.set_play_name(play or paths.PLAY_NAME)
    setup_logging()
    run_write_play(line_no_prefix)

@app.command()
def write_roles(
    line_no_prefix: bool = typer.Option(True, "--line_no_prefix/--no_line_no_prefix", help="prepend line numbers to each block"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Write build/text/<role>.md - all blocks for each role"""
    paths.set_play_name(play or paths.PLAY_NAME)
    setup_logging()
    run_write_roles(line_no_prefix)


@app.command("write-cues")
def write_cues(play: str | None = PLAY_OPTION) -> None:
    """Generate role cue text files into build/roles."""
    paths.set_play_name(play or paths.PLAY_NAME)
    setup_logging()
    run_write_cues()

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
    force: bool = typer.Option(False, "--force/--no-force", help="Force re-splitting even if outputs are newer"),
    play: str | None = PLAY_OPTION,
) -> None:
    paths.set_play_name(play or paths.PLAY_NAME)
    setup_logging()
    if role:
        play_obj = PlayTextParser().parse()
        valid_roles = {r.name for r in play_obj.roles} | {"_NARRATOR", "_CALLER"}
        if role not in valid_roles:
            raise typer.BadParameter(f"Unknown role: {role}")
    run_segments(
        role=role,
        part=part,
        silence_thresh=silence_thresh,
        separator_len_ms=separator_len_ms,
        chunk_size=chunk_size,
        verbose=verbose,
        chunk_exports=chunk_exports,
        chunk_export_size=chunk_export_size,
        force=force,
    )

@app.command()
def verify(
    too_short: float = typer.Option(0.5, help="Lower bound ratio of actual/expected"),
    too_long: float = typer.Option(2.0, help="Upper bound ratio of actual/expected"),
    play: str | None = PLAY_OPTION,
) -> None:
    paths.set_play_name(play or paths.PLAY_NAME)
    setup_logging()
    _run_verify(too_short, too_long)


def _run_verify(too_short: float = 0.5, too_long: float = 2.0) -> None:
    play = PlayTextParser().parse()
    builder = PlayPlanBuilder(play=play)
    plan = builder.build_audio_plan(parts=builder.list_parts())
    verifier = SegmentVerifier(plan=plan, too_short=too_short, too_long=too_long, play=play)
    verifier.verify_segments()


@app.command()
def check_recording(play: str | None = PLAY_OPTION) -> None:
    paths.set_play_name(play or paths.PLAY_NAME)
    setup_logging()
    run_check_recording()


@app.command("generate-timings")
def generate_timings(
    play: str | None = PLAY_OPTION,
    librivox: bool = typer.Option(False, help="Generate Librivox-style mp3s (one per part, no prelude)"),
    ) -> None:
    paths.set_play_name(play or paths.PLAY_NAME)
    setup_logging()
    run_generate_timings(librivox=librivox)


@app.command()
def audioplay(
    part: str = typer.Option(None, help="Part number to assemble, '_' for preamble, omit for all parts"),
    segment_spacing_ms: int = typer.Option(SEGMENT_SPACING_MS, help="Silence (ms) to insert between segments"),
    callouts: bool = typer.Option(True, help="Prepend each role line with its callout audio"),
    callout_spacing_ms: int = typer.Option(CALLOUT_SPACING_MS, help="Silence (ms) between callout and line"),
    minimal_callouts: bool = typer.Option(False, help="Reduce callouts during alternating two-person dialogue"),
    captions: bool = typer.Option(True, help="Generate captions (WebVTT) and mux into mp4 when possible"),
    generate_audio: bool = typer.Option(True, help="Write rendered audio (disable to only emit audio_plan.txt)"),
    librivox: bool = typer.Option(False, help="Generate Librivox-style mp3s (one per part, no prelude)"),
    audio_format: str = typer.Option("mp4", help="Output format: mp4 (default), mp3, or wav"),
    normalize_output: bool = typer.Option(True, help="Normalize the generated audioplay"),
    play: str | None = PLAY_OPTION,
) -> None:
    paths.set_play_name(play or paths.PLAY_NAME)
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
    play: str | None = PLAY_OPTION,
) -> None:
    """
    Normalize an audio file using ffmpeg loudnorm. Writes to a sibling 'normalized' folder.
    """
    paths.set_play_name(play or paths.PLAY_NAME)
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
    play: str | None = PLAY_OPTION,
) -> None:
    paths.set_play_name(play or paths.PLAY_NAME)
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
    run_write_callouts()
    run_write_callout_script()
    run_write_callouts()
    run_write_announcer()


def run_write_play(line_no_prefix: bool = True):
    play = PlayTextParser().parse()
    writer = PlayMarkdownWriter(play, prefix_line_nos=line_no_prefix)
    path = writer.to_markdown()
    logging.info("✅ wrote %s", path)
    return path


def run_write_roles(line_no_prefix: bool = True):
    play = PlayTextParser().parse()
    written_paths: list[Path] = []
    for role in play.roles:
        writer = RoleMarkdownWriter(role, reading_metadata=getattr(play, "reading_metadata", None), prefix_line_nos=line_no_prefix)
        path = writer.to_markdown()
        written_paths.append(path)
        logging.debug("✅ wrote %s", path)
    narrator_path = NarratorMarkdownWriter(
        play,
        reading_metadata=getattr(play, "reading_metadata", None),
        prefix_line_nos=line_no_prefix,
    ).to_markdown()
    written_paths.append(narrator_path)
    if written_paths:
        role_names = [r.name for r in play.roles] + ["_NARRATOR"]
        logging.info("✅ created .md files in %s for %s", written_paths[0].parent, ",".join(role_names))
    return written_paths


def run_write_callouts():
    play = PlayTextParser().parse()
    writer = CalloutsMarkdownWriter(play)
    path = writer.to_markdown()
    logging.info("✅ wrote %s", path)
    return path


def run_write_callout_script():
    play = PlayTextParser().parse()
    writer = CalloutScriptWriter(play)
    path = writer.to_markdown()
    logging.info("✅ wrote %s", path)
    return path

def run_write_announcer():
    play = PlayTextParser().parse()
    writer = AnnouncerScriptWriter(play)
    path = writer.to_yaml()
    logging.info("✅ wrote %s", path)
    return path


def run_write_cues():
    from role_cues import RoleCues
    from narration_cues import NarrationCues

    play = PlayTextParser().parse()
    RoleCues(play).write()
    NarrationCues(play).write()


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
    force: bool = False,
):
    play = PlayTextParser().parse()
    splitter = PlaySplitter(
        play=play,
        force=force,
        min_silence_ms=separator_len_ms,
        silence_thresh=silence_thresh,
        chunk_size=chunk_size,
        verbose=verbose,
        chunk_exports=chunk_exports,
        chunk_export_size=chunk_export_size,
    )
    return splitter.split_all(part_filter=part, role_filter=role)


def run_check_recording():
    timings_path = paths.AUDIO_OUT_DIR / "timings.csv"
    if not timings_path.exists():
        typer.echo(f"{timings_path} not found; run verify first.")
        raise typer.Exit(code=1)
    for line in summarize_recordings(timings_path):
        typer.echo(line)


def run_generate_timings(librivox: bool):
    generate_xlsx(librivox)


def run_audioplay(
    *,
    part: str | None = None,
    segment_spacing_ms: int = 500,
    callouts: bool = True,
    callout_spacing_ms: int = 125,
    minimal_callouts: bool = True,
    captions: bool = True,
    generate_audio: bool = True,
    librivox: bool = False,
    audio_format: str = "mp4",
    normalize_output: bool = True,
):
    if audio_format not in ("mp4", "mp3", "wav"):
        raise typer.BadParameter("audio-format must be one of: mp4, mp3, wav")
    play: Play = PlayTextParser().parse()
    if part is None:
        part_no = None
    else:
        part_no = int(part)

    builder = PlayBuilder(
        spacing_ms=segment_spacing_ms,
        include_callouts=callouts,
        callout_spacing_ms=callout_spacing_ms,
        minimal_callouts=minimal_callouts,
        audio_format=audio_format,
        part_gap_ms=2000,
        generate_audio=generate_audio,
        generate_captions=captions,
        librivox=librivox,
        play=play
    )
    out_paths = builder.build_audio(part_no=part_no)
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
    play = PlayTextParser().parse()
    builder = CueBuilder(
        play,
        response_delay_ms=response_delay_ms,
        max_cue_size_ms=max_cue_size_ms,
        include_prompts=include_prompts,
        callout_spacing_ms=callout_spacing_ms,
    )
    roles = [role] if role else [r.name for r in play.roles] + ["_NARRATOR"]
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
