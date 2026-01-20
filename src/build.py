#!/usr/bin/env python3
"""Build text artifacts, split audio segments, verify splits, and check recordings."""
from pathlib import Path
import logging
import sys
import shlex
from datetime import datetime
import time

import paths
import typer

from play_splitter import PlaySplitter
from recording_checker import summarize as summarize_recordings
from timings_xlsx import generate_xlsx
from play_builder import PlayBuilder
from play import Play, Part
from play_text_parser import PlayTextParser
from announcer_script_writer import AnnouncerScriptWriter
from announcer import LibrivoxAnnouncer
from play_markdown_writer import PlayMarkdownWriter
from role_markdown_writer import RoleMarkdownWriter
from narrator_markdown_writer import NarratorMarkdownWriter
from callouts_markdown_writer import CalloutsMarkdownWriter
from callout_script_writer import CalloutScriptWriter
from loudnorm.normalizer import Normalizer
from cue_builder import CueBuilder
from play_plan_builder import PlayPlanBuilder
from segment_verifier import SegmentVerifier
from whisper_model_store import WhisperModelStore
from role_audio_verifier import RoleAudioVerifier
from role_whisper_transcriber import RoleWhisperTranscriber
from unresolved_diffs import UnresolvedDiffs
from extra_audio_diff import ExtraAudioDiff
from match_audio_diff import MatchAudioDiff
from missing_audio_diff import MissingAudioDiff
from audio_verifier_summary_renderer import AudioVerifierSummaryRenderer
from audio_verifier_workbook_writer import AudioVerifierWorkbookWriter
from vad_config import VadConfig
from whisper_cache_cleaner import WhisperCacheCleaner
from huggingface_hub.errors import LocalEntryNotFoundError

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
MODEL_CHOICES = ("tiny", "base", "small", "med")
MODEL_NAME_MAP = {
    "tiny": "tiny.en",
    "base": "base.en",
    "small": "small.en",
    "med": "medium.en",
}
SUMMARY_FORMATS = {"text", "yaml"}


def setup_logging(paths_config: paths.PathConfig) -> None:
    paths_config.build_dir.mkdir(parents=True, exist_ok=True)
    paths_config.logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = paths_config.logs_dir / "build.log"
    if log_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_path.rename(paths_config.logs_dir / f"build-{timestamp}.log")

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
    for logger_name in (
        "faster_whisper",
        "faster_whisper.transcribe",
        "faster_whisper.vad",
    ):
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.ERROR)
        logger.propagate = False


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, play: str | None = PLAY_OPTION) -> None:
    play_name = play or paths.DEFAULT_PLAY_NAME
    cfg = paths.PathConfig(play_name)
    setup_logging(cfg)
    if ctx.invoked_subcommand is None:
        run_segments(paths_config=cfg)
        run_text(paths_config=cfg)
        run_audioplay(paths_config=cfg)

@app.command()
def text(play: str | None = PLAY_OPTION) -> None:
    """Build markdown artifacts."""
    cfg = paths.PathConfig(play or paths.DEFAULT_PLAY_NAME)
    setup_logging(cfg)
    run_text(paths_config=cfg)


@app.command()
def write_play(
    line_no_prefix: bool = typer.Option(True, "--line_no_prefix/--no_line_no_prefix", help="prepend line numbers to each block"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Write build/text/<play>.md"""
    cfg = paths.PathConfig(play or paths.DEFAULT_PLAY_NAME)
    setup_logging(cfg)
    run_write_play(line_no_prefix, paths_config=cfg)

@app.command()
def write_roles(
    line_no_prefix: bool = typer.Option(True, "--line_no_prefix/--no_line_no_prefix", help="prepend line numbers to each block"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Write build/text/<role>.md - all blocks for each role"""
    cfg = paths.PathConfig(play or paths.DEFAULT_PLAY_NAME)
    setup_logging(cfg)
    run_write_roles(line_no_prefix, paths_config=cfg)


@app.command("write-cues")
def write_cues(play: str | None = PLAY_OPTION) -> None:
    """Generate role cue text files into build/roles."""
    cfg = paths.PathConfig(play or paths.DEFAULT_PLAY_NAME)
    setup_logging(cfg)
    run_write_cues(paths_config=cfg)

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
    cfg = paths.PathConfig(play or paths.DEFAULT_PLAY_NAME)
    setup_logging(cfg)
    if role:
        play_obj = PlayTextParser(paths_config=cfg).parse()
        valid_roles = {r.name for r in play_obj.roles} | {"_NARRATOR", "_CALLER", "_ANNOUNCER"}
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
        paths_config=cfg,
    )

@app.command()
def verify(
    too_short: float = typer.Option(0.5, help="Lower bound ratio of actual/expected"),
    too_long: float = typer.Option(2.0, help="Upper bound ratio of actual/expected"),
    play: str | None = PLAY_OPTION,
) -> None:
    cfg = paths.PathConfig(play or paths.DEFAULT_PLAY_NAME)
    setup_logging(cfg)
    _run_verify(too_short, too_long, paths_config=cfg)


def _run_verify(too_short: float = 0.5, too_long: float = 2.0, paths_config: paths.PathConfig | None = None) -> None:
    cfg = paths_config or paths.current()
    play = PlayTextParser(paths_config=cfg).parse()
    builder = PlayPlanBuilder(play=play, paths=cfg)
    plan = builder.build_audio_plan(parts=builder.list_parts())
    verifier = SegmentVerifier(plan=plan, too_short=too_short, too_long=too_long, play=play, paths=cfg)
    verifier.verify_segments()


@app.command()
def check_recording(play: str | None = PLAY_OPTION) -> None:
    cfg = paths.PathConfig(play or paths.DEFAULT_PLAY_NAME)
    setup_logging(cfg)
    run_check_recording(paths_config=cfg)


@app.command("generate-timings")
def generate_timings(
    play: str | None = PLAY_OPTION,
    librivox: bool = typer.Option(False, help="Use Librivox preamble/epilog when computing timings"),
    segment_spacing_ms: int = typer.Option(SEGMENT_SPACING_MS, "--segment-spacing-ms", help="Silence (ms) between segments"),
    callouts: bool = typer.Option(True, help="Include callout audio when computing timings"),
    callout_spacing_ms: int = typer.Option(CALLOUT_SPACING_MS, "--callout-spacing-ms", help="Silence (ms) between callout and line"),
    minimal_callouts: bool = typer.Option(False, help="Reduce callouts during alternating two-person dialogue"),
    include_decorations: bool = typer.Option(
        True,
        "--include-decorations/--no-include-decorations",
        help="Include callouts and announcer clips in timings output",
    ),
    ) -> None:
    cfg = paths.PathConfig(play or paths.DEFAULT_PLAY_NAME)
    setup_logging(cfg)
    run_generate_timings(
        librivox=librivox,
        segment_spacing_ms=segment_spacing_ms,
        callouts=callouts,
        callout_spacing_ms=callout_spacing_ms,
        minimal_callouts=minimal_callouts,
        include_decorations=include_decorations,
        paths_config=cfg,
    )


@app.command("verify-audio")
def verify_audio(
    role: str | None = typer.Option(None, "--role", "-r", help="Role to verify (omit for all roles)"),
    recording: Path | None = typer.Option(None, "--recording", help="Override recording WAV path"),
    output: Path | None = typer.Option(None, "--out", help="Output XLSX path"),
    model: str = typer.Option("med", "--model", "-m", help="Whisper model: tiny, base, small, med"),
    vad_filter: bool = typer.Option(True, "--vad-filter/--no-vad-filter", help="Enable Silero VAD filtering"),
    vad_threshold: float | None = typer.Option(
        None,
        "--vad-threshold",
        help="Speech probability threshold (default: 0.5)",
    ),
    vad_neg_threshold: float | None = typer.Option(
        None,
        "--vad-neg-threshold",
        help="End-of-speech threshold (default: max(vad-threshold - 0.15, 0.01))",
    ),
    vad_min_speech_duration_ms: int | None = typer.Option(
        None,
        "--vad-min-speech-duration-ms",
        help="Drop speech chunks shorter than this duration (default: 0)",
    ),
    vad_max_speech_duration_s: float | None = typer.Option(
        None,
        "--vad-max-speech-duration-s",
        help="Split speech chunks longer than this duration (default: model chunk length)",
    ),
    vad_min_silence_duration_ms: int | None = typer.Option(
        None,
        "--vad-min-silence-duration-ms",
        help="Required silence before splitting chunks (default: 160)",
    ),
    vad_speech_pad_ms: int | None = typer.Option(
        None,
        "--vad-speech-pad-ms",
        help="Padding added to each side of speech chunks (default: 400)",
    ),
    no_speech_threshold: float | None = typer.Option(
        None,
        "--no-speech-threshold",
        help="Drop segments with speech probability below this (default: model)",
    ),
    log_prob_threshold: float | None = typer.Option(
        None,
        "--log-prob-threshold",
        help="Drop segments with average log prob below this (default: model)",
    ),
    condition_on_previous_text: bool = typer.Option(
        True,
        "--condition-on-previous-text/--no-condition-on-previous-text",
        help="Condition on previous text during decoding",
    ),
    initial_prompt: str | None = typer.Option(
        None,
        "--initial-prompt",
        help="Initial prompt to bias Whisper transcription",
    ),
    homophone_max_words: int = typer.Option(
        2,
        "--homophone-max-words",
        help="Maximum words per homophone phrase (default: 2)",
    ),
    remove_fillers: bool = typer.Option(
        False,
        "--remove-fillers/--keep-fillers",
        help="Drop filler words like 'um' and 'uh' during alignment",
    ),
    summary: bool = typer.Option(True, "--summary/--no-summary", help="Write concise summary to console"),
    summary_format: str = typer.Option("text", "--summary-format", help="Summary format: text or yaml"),
    play: str | None = PLAY_OPTION,
) -> None:
    cfg = paths.PathConfig(play or paths.DEFAULT_PLAY_NAME)
    setup_logging(cfg)
    summary_key = summary_format.lower().strip()
    if summary_key not in SUMMARY_FORMATS:
        raise typer.BadParameter(
            f"Unknown summary format: {summary_format}. Choose from {', '.join(sorted(SUMMARY_FORMATS))}."
        )
    play_obj = PlayTextParser(paths_config=cfg).parse()
    valid_roles = {r.name for r in play_obj.roles} | {"_NARRATOR", "_CALLER", "_ANNOUNCER"}
    roles_to_verify = [role] if role else sorted(valid_roles)
    if recording and len(roles_to_verify) > 1:
        raise typer.BadParameter("Cannot use --recording without --role")
    if output and len(roles_to_verify) > 1:
        raise typer.BadParameter("Cannot use --out without --role")
    for role_name in roles_to_verify:
        if role_name not in valid_roles:
            raise typer.BadParameter(f"Unknown role: {role_name}")
    model_key = model.lower().strip()
    if model_key not in MODEL_CHOICES:
        raise typer.BadParameter(f"Unknown model: {model}. Choose from {', '.join(MODEL_CHOICES)}.")
    model_name = MODEL_NAME_MAP[model_key]
    store = WhisperModelStore(
        paths=cfg,
        device="cpu",
        compute_type="int8",
        local_files_only=True,
    )
    vad_config = VadConfig.from_overrides(
        threshold=vad_threshold,
        neg_threshold=vad_neg_threshold,
        min_speech_duration_ms=vad_min_speech_duration_ms,
        max_speech_duration_s=vad_max_speech_duration_s,
        min_silence_duration_ms=vad_min_silence_duration_ms,
        speech_pad_ms=vad_speech_pad_ms,
    )
    total_roles = len(roles_to_verify)
    combined_diffs: dict[str, list] = {}
    vetted_ids_by_role: dict[str, set[str]] = {}
    for idx, role_name in enumerate(roles_to_verify, start=1):
        logging.info("Verifying role %s (%d/%d)", role_name, idx, total_roles)
        verifier = RoleAudioVerifier(
            role=role_name,
            paths=cfg,
            play=play_obj,
            model_name=model_name,
            whisper_store=store,
            vad_filter=vad_filter,
            vad_config=vad_config,
            no_speech_threshold=no_speech_threshold,
            log_prob_threshold=log_prob_threshold,
            condition_on_previous_text=condition_on_previous_text,
            initial_prompt=initial_prompt,
            homophone_max_words=homophone_max_words,
            remove_fillers=remove_fillers,
        )
        vetted_ids_by_role[role_name] = verifier.vetted_ids()
        try:
            results = verifier.verify(recording_path=recording)
        except LocalEntryNotFoundError as exc:
            raise typer.BadParameter(
                f"Whisper model '{model_name}' not cached. Run: python src/build.py whisper-init --model {model_name}"
            ) from exc
        unresolved = UnresolvedDiffs()
        for expected, actual, segment_id in verifier.unresolved_replacements(results):
            unresolved.add(expected, actual, segment_id=segment_id)
        diffs = verifier.build_diffs(results)
        if role is None:
            combined_diffs[role_name] = diffs
        write_start = time.perf_counter()
        out_path = verifier.write_xlsx(results, out_path=output)
        write_elapsed = time.perf_counter() - write_start
        logging.info("Wrote %s in %.2fs", out_path, write_elapsed)
        missing_count = sum(1 for diff in diffs if isinstance(diff, MissingAudioDiff))
        extra_count = sum(1 for diff in diffs if isinstance(diff, ExtraAudioDiff))
        partial_count = sum(
            1
            for diff in diffs
            if isinstance(diff, MatchAudioDiff) and diff.match_quality > 0
        )
        if missing_count:
            symbol = "❌"
        elif extra_count:
            symbol = "⚠️"
        else:
            symbol = "✅"
        logging.info(
            "%s%s: %d/%d/%d missing/extra/partials ... see %s",
            symbol,
            role_name,
            missing_count,
            extra_count,
            partial_count,
            out_path,
        )
        if summary:
            renderer = AudioVerifierSummaryRenderer(format=summary_key)
            logging.info("\n%s", renderer.render(results))
        unresolved_path = cfg.build_dir / f"{role_name}_unresolved_diffs.yaml"
        unresolved.write(unresolved_path)
    if role is None:
        combined_path = cfg.audio_out_dir / "audio-verifier.xlsx"
        writer = AudioVerifierWorkbookWriter()
        combined_start = time.perf_counter()
        writer.write(
            combined_diffs,
            combined_path,
            role_order=roles_to_verify,
            vetted_ids_by_role=vetted_ids_by_role,
        )
        combined_elapsed = time.perf_counter() - combined_start
        logging.info(
            "Wrote combined audio verification workbook to %s in %.2fs",
            combined_path,
            combined_elapsed,
        )


@app.command("whisper")
def whisper(
    role: str = typer.Option(..., "--role", "-r", help="Role to transcribe"),
    model: str = typer.Option("med", "--model", "-m", help="Whisper model: tiny, base, small, med"),
    vad_filter: bool = typer.Option(True, "--vad-filter/--no-vad-filter", help="Enable Silero VAD filtering"),
    clip_from_ms: int = typer.Option(
        0,
        "--clip-from-ms",
        help="Start offset in ms for clipping (default: 0)",
    ),
    clip_length_ms: int | None = typer.Option(
        None,
        "--clip-length-ms",
        help="Clip duration in ms (default: full length)",
    ),
    vad_threshold: float | None = typer.Option(
        None,
        "--vad-threshold",
        help="Speech probability threshold (default: 0.5)",
    ),
    vad_neg_threshold: float | None = typer.Option(
        None,
        "--vad-neg-threshold",
        help="End-of-speech threshold (default: max(vad-threshold - 0.15, 0.01))",
    ),
    vad_min_speech_duration_ms: int | None = typer.Option(
        None,
        "--vad-min-speech-duration-ms",
        help="Drop speech chunks shorter than this duration (default: 0)",
    ),
    vad_max_speech_duration_s: float | None = typer.Option(
        None,
        "--vad-max-speech-duration-s",
        help="Split speech chunks longer than this duration (default: model chunk length)",
    ),
    vad_min_silence_duration_ms: int | None = typer.Option(
        None,
        "--vad-min-silence-duration-ms",
        help="Required silence before splitting chunks (default: 160)",
    ),
    vad_speech_pad_ms: int | None = typer.Option(
        None,
        "--vad-speech-pad-ms",
        help="Padding added to each side of speech chunks (default: 400)",
    ),
    no_speech_threshold: float | None = typer.Option(
        None,
        "--no-speech-threshold",
        help="Drop segments with speech probability below this (default: model)",
    ),
    log_prob_threshold: float | None = typer.Option(
        None,
        "--log-prob-threshold",
        help="Drop segments with average log prob below this (default: model)",
    ),
    condition_on_previous_text: bool = typer.Option(
        True,
        "--condition-on-previous-text/--no-condition-on-previous-text",
        help="Condition on previous text during decoding",
    ),
    initial_prompt: str | None = typer.Option(
        None,
        "--initial-prompt",
        help="Initial prompt to bias Whisper transcription",
    ),
    play: str | None = PLAY_OPTION,
) -> None:
    cfg = paths.PathConfig(play or paths.DEFAULT_PLAY_NAME)
    setup_logging(cfg)
    model_key = model.lower().strip()
    if model_key not in MODEL_CHOICES:
        raise typer.BadParameter(f"Unknown model: {model}. Choose from {', '.join(MODEL_CHOICES)}.")
    model_name = MODEL_NAME_MAP[model_key]
    vad_config = VadConfig.from_overrides(
        threshold=vad_threshold,
        neg_threshold=vad_neg_threshold,
        min_speech_duration_ms=vad_min_speech_duration_ms,
        max_speech_duration_s=vad_max_speech_duration_s,
        min_silence_duration_ms=vad_min_silence_duration_ms,
        speech_pad_ms=vad_speech_pad_ms,
    )
    transcriber = RoleWhisperTranscriber(
        role=role,
        paths=cfg,
        model_name=model_name,
        vad_filter=vad_filter,
        vad_config=vad_config,
        no_speech_threshold=no_speech_threshold,
        log_prob_threshold=log_prob_threshold,
        condition_on_previous_text=condition_on_previous_text,
        initial_prompt=initial_prompt,
        clip_from_ms=clip_from_ms,
        clip_length_ms=clip_length_ms,
    )
    try:
        transcriber.transcribe()
    except LocalEntryNotFoundError as exc:
        raise typer.BadParameter(
            f"Whisper model '{model_name}' not cached. Run: python src/build.py whisper-init --model {model_name}"
        ) from exc


@app.command("clear-whisper-cache")
def clear_whisper_cache(
    role: str | None = typer.Option(None, "--role", "-r", help="Role to clear (omit for all roles)"),
    play: str | None = PLAY_OPTION,
) -> None:
    cfg = paths.PathConfig(play or paths.DEFAULT_PLAY_NAME)
    setup_logging(cfg)
    cleaner = WhisperCacheCleaner(paths=cfg)
    removed = cleaner.clear(role)
    if role:
        logging.info("Cleared %d cached transcription(s) for %s", removed, role)
    else:
        logging.info("Cleared %d cached transcription(s)", removed)


@app.command("whisper-init")
def whisper_init(
    model: list[str] = typer.Option(None, "--model", "-m", help="Whisper model name(s) to cache"),
    device: str = typer.Option("cpu", help="Device to load the model for caching"),
    compute_type: str = typer.Option("int8", help="Compute type for loading cached models"),
    play: str | None = PLAY_OPTION,
) -> None:
    cfg = paths.PathConfig(play or paths.DEFAULT_PLAY_NAME)
    setup_logging(cfg)
    model_names = model if model else ["tiny.en"]
    store = WhisperModelStore(
        paths=cfg,
        device=device,
        compute_type=compute_type,
        local_files_only=False,
    )
    for model_name in model_names:
        store.load(model_name)
    logging.info("✅ cached whisper model(s) in %s", store.cache_dir)


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
    prepare: bool = typer.Option(True, help="Ensure text/scripts and split segments are up to date before building"),
    play: str | None = PLAY_OPTION,
) -> None:
    cfg = paths.PathConfig(play or paths.DEFAULT_PLAY_NAME)
    setup_logging(cfg)
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
        paths_config=cfg,
        prepare=prepare,
    )


@app.command()
def normalize(
    src: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True),
    play: str | None = PLAY_OPTION,
) -> None:
    """
    Normalize an audio file using ffmpeg loudnorm. Writes to a sibling 'normalized' folder.
    """
    cfg = paths.PathConfig(play or paths.DEFAULT_PLAY_NAME)
    setup_logging(cfg)
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
    cfg = paths.PathConfig(play or paths.DEFAULT_PLAY_NAME)
    setup_logging(cfg)
    run_cues(
        role=role,
        response_delay_ms=response_delay_ms,
        max_cue_size_ms=max_cue_size_ms,
        include_prompts=include_prompts,
        callout_spacing_ms=callout_spacing_ms,
        paths_config=cfg,
    )


# Helper functions (non-Typer) -----------------------------------------------

def run_text(line_no_prefix: bool = True, paths_config: paths.PathConfig | None = None) -> None:
    cfg = paths_config or paths.current()
    run_write_play(line_no_prefix, paths_config=cfg)
    run_write_roles(line_no_prefix, paths_config=cfg)
    run_write_callouts(paths_config=cfg)
    run_write_callout_script(paths_config=cfg)
    run_write_callouts(paths_config=cfg)
    run_write_announcer(paths_config=cfg)


def run_write_play(line_no_prefix: bool = True, paths_config: paths.PathConfig | None = None):
    cfg = paths_config or paths.current()
    play = PlayTextParser(paths_config=cfg).parse()
    writer = PlayMarkdownWriter(play, paths=cfg, prefix_line_nos=line_no_prefix)
    path = writer.to_markdown()
    logging.info("✅ wrote %s", path)
    return path


def run_write_roles(line_no_prefix: bool = True, paths_config: paths.PathConfig | None = None):
    cfg = paths_config or paths.current()
    play = PlayTextParser(paths_config=cfg).parse()
    written_paths: list[Path] = []
    for role in play.roles:
        writer = RoleMarkdownWriter(
            role,
            reading_metadata=getattr(play, "reading_metadata", None),
            paths=cfg,
            prefix_line_nos=line_no_prefix,
        )
        path = writer.to_markdown()
        written_paths.append(path)
        logging.debug("✅ wrote %s", path)
    narrator_path = NarratorMarkdownWriter(
        play,
        reading_metadata=getattr(play, "reading_metadata", None),
        paths=cfg,
        prefix_line_nos=line_no_prefix,
    ).to_markdown()
    written_paths.append(narrator_path)
    if written_paths:
        role_names = [r.name for r in play.roles] + ["_NARRATOR"]
        logging.info("✅ created .md files in %s for %s", written_paths[0].parent, ",".join(role_names))
    return written_paths


def run_write_callouts(paths_config: paths.PathConfig | None = None):
    cfg = paths_config or paths.current()
    play = PlayTextParser(paths_config=cfg).parse()
    writer = CalloutsMarkdownWriter(play, paths=cfg)
    path = writer.to_markdown()
    logging.info("✅ wrote %s", path)
    return path


def run_write_callout_script(paths_config: paths.PathConfig | None = None):
    cfg = paths_config or paths.current()
    play = PlayTextParser(paths_config=cfg).parse()
    writer = CalloutScriptWriter(play, paths=cfg)
    path = writer.to_markdown()
    logging.info("✅ wrote %s", path)
    return path

def run_write_announcer(paths_config: paths.PathConfig | None = None):
    cfg = paths_config or paths.current()
    play = PlayTextParser(paths_config=cfg).parse()
    announcer = LibrivoxAnnouncer(play)
    writer = AnnouncerScriptWriter(announcer=announcer, paths=cfg)
    path = writer.to_markdown()
    logging.info("✅ wrote %s", path)
    return path


def run_write_cues(paths_config: paths.PathConfig | None = None):
    from role_cues import RoleCues
    from narration_cues import NarrationCues

    cfg = paths_config or paths.current()
    play = PlayTextParser(paths_config=cfg).parse()
    RoleCues(play, paths=cfg).write()
    NarrationCues(play, paths=cfg).write()


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
    paths_config: paths.PathConfig | None = None,
):
    cfg = paths_config or paths.current()
    play = PlayTextParser(paths_config=cfg).parse()
    splitter = PlaySplitter(
        play=play,
        paths=cfg,
        force=force,
        min_silence_ms=separator_len_ms,
        silence_thresh=silence_thresh,
        chunk_size=chunk_size,
        verbose=verbose,
        chunk_exports=chunk_exports,
        chunk_export_size=chunk_export_size,
    )
    return splitter.split_all(part_filter=part, role_filter=role)


def run_check_recording(paths_config: paths.PathConfig | None = None):
    cfg = paths_config or paths.current()
    timings_path = cfg.audio_out_dir / "timings.csv"
    if not timings_path.exists():
        typer.echo(f"{timings_path} not found; run verify first.")
        raise typer.Exit(code=1)
    for line in summarize_recordings(timings_path):
        typer.echo(line)


def run_generate_timings(
    librivox: bool,
    segment_spacing_ms: int = SEGMENT_SPACING_MS,
    callouts: bool = True,
    callout_spacing_ms: int = CALLOUT_SPACING_MS,
    minimal_callouts: bool = False,
    include_decorations: bool = True,
    paths_config: paths.PathConfig | None = None,
):
    cfg = paths_config or paths.current()
    play = PlayTextParser(paths_config=cfg).parse()
    part_ids = [p.part_no for p in play.parts if p.part_no is not None]
    if librivox and len(part_ids) > 1:
        for part_no in part_ids:
            generate_xlsx(
                librivox=librivox,
                part_no=part_no,
                include_callouts=callouts,
                callout_spacing_ms=callout_spacing_ms,
                minimal_callouts=minimal_callouts,
                segment_spacing_ms=segment_spacing_ms,
                include_decorations=include_decorations,
                paths_config=cfg,
            )
        return
    generate_xlsx(
        librivox=librivox,
        include_callouts=callouts,
        callout_spacing_ms=callout_spacing_ms,
        minimal_callouts=minimal_callouts,
        segment_spacing_ms=segment_spacing_ms,
        include_decorations=include_decorations,
        paths_config=cfg,
    )


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
    prepare: bool = True,
    paths_config: paths.PathConfig | None = None,
):
    if audio_format not in ("mp4", "mp3", "wav"):
        raise typer.BadParameter("audio-format must be one of: mp4, mp3, wav")
    cfg = paths_config or paths.current()
    if prepare:
        logging.info("Preparing text artifacts and split segments before audioplay")
        run_text(line_no_prefix=True, paths_config=cfg)
        run_segments(paths_config=cfg)
    play: Play = PlayTextParser(paths_config=cfg).parse()
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
        play=play,
        paths=cfg,
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
    paths_config: paths.PathConfig | None = None,
):
    cfg = paths_config or paths.current()
    play = PlayTextParser(paths_config=cfg).parse()
    builder = CueBuilder(
        play,
        paths=cfg,
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
