#!/usr/bin/env python3
"""Build text artifacts, split audio segments, verify splits, and check recordings."""
from pathlib import Path
import logging
import sys
import shlex
from datetime import datetime
import time

from stager.shared import paths
import typer
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from stager.audio.segment_build_service import SegmentBuildService
from stager.verification.recording_checker import RecordingChecker
from stager.audiobook.audio_play_build_service import AudioPlayBuildService
from stager.audiobook.timing_build_service import TimingBuildService
from stager.domain.play import Play, Part
from stager.text.text_artifact_builder import TextArtifactBuilder
from stager.loudnorm.normalizer import Normalizer
from stager.cues.cue_build_service import CueBuildService
from stager.audiobook.play_plan_builder import PlayPlanBuilder
from stager.playbook.playbook_builder import PlaybookBuilder
from stager.playbook.playbook_progress_reporter import PlaybookProgressReporter
from stager.scriptwright import ProductionPlayLoader, ScriptWright
from stager.linerecorder.recording_request_builder import RecordingRequestBuilder
from stager.linerecorder.role_recordings_importer import RecordingImportProcessingOptions, RoleRecordingsImporter
from stager.verification.segment_verifier import SegmentVerifier
from stager.transcription.whisper_model_store import WhisperModelStore
from stager.verification.role_audio_verifier import RoleAudioVerifier
from stager.transcription.role_whisper_transcriber import RoleWhisperTranscriber
from stager.verification.unresolved_diffs import UnresolvedDiffs
from stager.verification.extra_audio_diff import ExtraAudioDiff
from stager.verification.match_audio_diff import MatchAudioDiff
from stager.verification.missing_audio_diff import MissingAudioDiff
from stager.verification.audio_verifier_summary_renderer import AudioVerifierSummaryRenderer
from stager.verification.audio_verifier_workbook_writer import AudioVerifierWorkbookWriter
from stager.transcription.vad_config import VadConfig
from stager.transcription.whisper_cache_cleaner import WhisperCacheCleaner
from stager.audio.audio_check import AudioCheck
from stager.audio.segment_audio_player import SegmentAudioPlayer
from stager.audio.audacity_recording_exporter import AudacityRecordingExporter
from stager.shared.build_type_resolver import BuildTypeResolver
from stager.shared.progress_reporter import ProgressReporter
from huggingface_hub.errors import LocalEntryNotFoundError

from stager.audio.spacing import (
  CALLOUT_SPACING_MS,
  SEGMENT_SPACING_MS
)

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)
text_app = typer.Typer(
    add_completion=False,
    help="Build markdown artifacts",
    pretty_exceptions_enable=False,
)
whisper_app = typer.Typer(
    add_completion=False,
    help="Whisper transcription tools",
    pretty_exceptions_enable=False,
)
scriptwright_app = typer.Typer(
    add_completion=False,
    help="Convert source scripts into locked production.md",
    pretty_exceptions_enable=False,
)
app.add_typer(text_app, name="text", rich_help_panel="build")
app.add_typer(whisper_app, name="whisper", rich_help_panel="utility")
app.add_typer(scriptwright_app, name="scriptwright", rich_help_panel="build")
PLAY_OPTION = typer.Option(
    None,
    "--play",
    "-p",
    help="Play directory name under plays/ (default: play-config.yaml play_id)",
)
MODEL_CHOICES = ("tiny", "base", "small", "med")
MODEL_NAME_MAP = {
    "tiny": "tiny.en",
    "base": "base.en",
    "small": "small.en",
    "med": "medium.en",
}
SUMMARY_FORMATS = {"text", "yaml"}


class RichPlaybookProgressReporter:
    def __init__(self, progress: Progress) -> None:
        self.progress = progress
        self.task_id: TaskID | None = None

    def start_audio_packaging(self, total: int) -> None:
        self.task_id = self.progress.add_task("Packaging Playbook audio", total=total)

    def audio_packaged(self, role: str, segment_id: str, category: str) -> None:
        if self.task_id is None:
            return
        self.progress.update(
            self.task_id,
            description=f"Packaging {category} {role} {segment_id}",
            advance=1,
        )

    def finish_audio_packaging(self) -> None:
        if self.task_id is None:
            return
        self.progress.update(self.task_id, description="Packaged Playbook audio")
        self.progress.stop_task(self.task_id)


class RichProgressReporter:
    def __init__(self, progress: Progress) -> None:
        self.progress = progress
        self.task_id: TaskID | None = None

    def start(self, total: int, description: str) -> None:
        self.task_id = self.progress.add_task(description, total=total)

    def advance(self, description: str | None = None) -> None:
        if self.task_id is None:
            return
        kwargs = {"advance": 1}
        if description is not None:
            kwargs["description"] = description
        self.progress.update(self.task_id, **kwargs)

    def finish(self, description: str | None = None) -> None:
        if self.task_id is None:
            return
        if description is not None:
            self.progress.update(self.task_id, description=description)
        self.progress.stop_task(self.task_id)


def rich_progress() -> Progress:
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    )


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


def load_production_play(paths_config: paths.PathConfig) -> Play:
    return ProductionPlayLoader(paths_config=paths_config).load()


@scriptwright_app.command("lock")
def scriptwright_lock(
    force: bool = typer.Option(False, "--force/--no-force", help="Overwrite an existing locked production.md"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Create locked production.md from the current play.txt source."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    output_path = ScriptWright(paths_config=cfg).write_locked(force=force)
    typer.echo(f"Wrote {paths.display_path(output_path)}")


@scriptwright_app.command("reconcile")
def scriptwright_reconcile(
    play: str | None = PLAY_OPTION,
) -> None:
    """Reconcile source changes into an existing locked production.md."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    ScriptWright(paths_config=cfg).reconcile()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, play: str | None = PLAY_OPTION) -> None:
    play_name = play or paths.default_play_name()
    cfg = paths.PathConfig(play_name)
    setup_logging(cfg)
    if ctx.invoked_subcommand is None:
        typer.echo("use './main audioplay --prepare' to build the audioplay or './main --help' to see a list of commands")
        raise typer.Exit(code=1)

@text_app.callback(invoke_without_command=True)
def text(
    ctx: typer.Context,
    play: str | None = PLAY_OPTION,
    librivox: bool | None = typer.Option(None, "--librivox/--no-librivox", help="Override configured build type for announcer text"),
) -> None:
    """Build markdown artifacts."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    if ctx.invoked_subcommand is None:
        build_type = BuildTypeResolver(paths_config=cfg, librivox_override=librivox).resolve()
        run_text(paths_config=cfg, build_type=build_type)


@text_app.command("write-play", hidden=True)
def write_play(
    line_no_prefix: bool = typer.Option(True, "--line_no_prefix/--no_line_no_prefix", help="prepend line numbers to each block"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Write build/text/<play>.md"""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    run_write_play(line_no_prefix, paths_config=cfg)

@text_app.command("write-roles", hidden=True)
def write_roles(
    line_no_prefix: bool = typer.Option(True, "--line_no_prefix/--no_line_no_prefix", help="prepend line numbers to each block"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Write build/text/<role>.md - all blocks for each role"""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    run_write_roles(line_no_prefix, paths_config=cfg)


@text_app.command("write-cues", hidden=True)
def write_cues(play: str | None = PLAY_OPTION) -> None:
    """Generate role cue text files into build/roles."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    run_write_cues(paths_config=cfg)

@app.command("segments", rich_help_panel="build")
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
    librivox: bool | None = typer.Option(None, "--librivox/--no-librivox", help="Override configured build type for announcer splitting"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Split role recordings into segments using silence detection."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    if role:
        play_obj = load_production_play(cfg)
        valid_roles = {r.name for r in play_obj.roles} | {"_NARRATOR", "_CALLER", "_ANNOUNCER"}
        if role not in valid_roles:
            raise typer.BadParameter(f"Unknown role: {role}")
    with rich_progress() as progress:
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
            build_type=BuildTypeResolver(paths_config=cfg, librivox_override=librivox).resolve(),
            progress_reporter=RichProgressReporter(progress),
        )

@app.command("verify", rich_help_panel="verify")
def verify(
    too_short: float = typer.Option(0.5, help="Lower bound ratio of actual/expected"),
    too_long: float = typer.Option(2.0, help="Upper bound ratio of actual/expected"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Verify split segments against expected durations."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    _run_verify(too_short, too_long, paths_config=cfg)


def _run_verify(too_short: float = 0.5, too_long: float = 2.0, paths_config: paths.PathConfig | None = None) -> None:
    cfg = paths_config or paths.current()
    play = load_production_play(cfg)
    builder = PlayPlanBuilder(play=play, paths=cfg)
    plan = builder.build_audio_plan()
    verifier = SegmentVerifier(plan=plan, too_short=too_short, too_long=too_long, play=play, paths=cfg)
    verifier.verify_segments()


@app.command("check-recording", rich_help_panel="verify")
def check_recording(play: str | None = PLAY_OPTION) -> None:
    """Summarize missing and suspect split segments by role."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    run_check_recording(paths_config=cfg)


@app.command("generate-timings", rich_help_panel="verify")
def generate_timings(
    play: str | None = PLAY_OPTION,
    librivox: bool | None = typer.Option(None, "--librivox/--no-librivox", help="Use Librivox preamble/epilog when computing timings"),
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
    """Generate timings spreadsheets for the current play."""
    cfg = paths.PathConfig(play or paths.default_play_name())
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


@app.command("verify-audio", rich_help_panel="verify")
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
    """Transcribe and compare role audio to script text, outputting diffs."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    summary_key = summary_format.lower().strip()
    if summary_key not in SUMMARY_FORMATS:
        raise typer.BadParameter(
            f"Unknown summary format: {summary_format}. Choose from {', '.join(sorted(SUMMARY_FORMATS))}."
        )
    play_obj = load_production_play(cfg)
    valid_roles = {r.name for r in play_obj.roles} | {"_NARRATOR", "_CALLER", "_ANNOUNCER"}
    roles_to_verify = [role] if role else sorted(valid_roles)
    if recording and len(roles_to_verify) > 1:
        raise typer.BadParameter("Cannot use --recording without --role")
    if output and len(roles_to_verify) > 1:
        raise typer.BadParameter("Cannot use --out without --role")
    for role_name in roles_to_verify:
        if role_name not in valid_roles:
            raise typer.BadParameter(f"Unknown role: {role_name}")
    AudacityRecordingExporter(paths=cfg).export_recordings()
    model_key = model.lower().strip()
    if model_key not in MODEL_CHOICES:
        raise typer.BadParameter(f"Unknown model: {model}. Choose from {', '.join(MODEL_CHOICES)}.")
    model_name = MODEL_NAME_MAP[model_key]
    effective_build_type = BuildTypeResolver(paths_config=cfg).resolve()
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
    ignored_ids_by_role: dict[str, set[str]] = {}
    problems_ids_by_role: dict[str, set[str]] = {}
    with rich_progress() as progress:
        progress_reporter = RichProgressReporter(progress)
        progress_reporter.start(total_roles, "Verifying role audio")
        for role_name in roles_to_verify:
            verifier = RoleAudioVerifier(
                role=role_name,
                paths=cfg,
                play=play_obj,
                model_name=model_name,
                build_type=effective_build_type,
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
            ignored_ids_by_role[role_name] = verifier.ignored_ids()
            problems_ids_by_role[role_name] = verifier.problems_ids()
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
            logging.info("Wrote %s in %.2fs", paths.display_path(out_path), write_elapsed)
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
                paths.display_path(out_path),
            )
            if summary:
                renderer = AudioVerifierSummaryRenderer(format=summary_key)
                logging.info("\n%s", renderer.render(results))
            unresolved_path = cfg.build_dir / f"{role_name}_unresolved_diffs.yaml"
            unresolved.write(unresolved_path)
            progress_reporter.advance(f"Verified {role_name}")
        progress_reporter.finish("Verified role audio")
    if role is None:
        combined_path = cfg.audio_out_dir / "audio-verifier.xlsx"
        writer = AudioVerifierWorkbookWriter()
        combined_start = time.perf_counter()
        writer.write(
            combined_diffs,
            combined_path,
            role_order=roles_to_verify,
            vetted_ids_by_role=vetted_ids_by_role,
            ignored_ids_by_role=ignored_ids_by_role,
            problems_ids_by_role=problems_ids_by_role,
        )
        combined_elapsed = time.perf_counter() - combined_start
        logging.info(
            "Wrote combined audio verification workbook to %s in %.2fs",
            paths.display_path(combined_path),
            combined_elapsed,
        )


@whisper_app.callback(invoke_without_command=True)
def whisper(
    ctx: typer.Context,
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
    """Run a raw Whisper transcription for a role recording."""
    if ctx.invoked_subcommand is not None:
        return
    cfg = paths.PathConfig(play or paths.default_play_name())
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


@whisper_app.command("clear-whisper-cache", hidden=True)
def clear_whisper_cache(
    role: str | None = typer.Option(None, "--role", "-r", help="Role to clear (omit for all roles)"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Clear cached Whisper transcriptions for the current play."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    cleaner = WhisperCacheCleaner(paths=cfg)
    removed = cleaner.clear(role)
    if role:
        logging.info("Cleared %d cached transcription(s) for %s", removed, role)
    else:
        logging.info("Cleared %d cached transcription(s)", removed)


@app.command("play", rich_help_panel="utility")
def play_audio(
    target: str = typer.Argument(
        ...,
        metavar="TARGET",
        help="Role name or segment id to play (segment ids look like 1_17_3)",
    ),
    offset_ms: int = typer.Argument(
        0,
        metavar="OFFSET-MS",
        help="Start offset in milliseconds (default: 0)",
    ),
    continue_play: bool = typer.Option(
        False,
        "--continue",
        help="Keep playing past the detected silence",
    ),
    offset_mod: float = typer.Option(
        0.0,
        "--offset-mod",
        help="Seconds to adjust the start time (negative for earlier)",
    ),
    play: str | None = PLAY_OPTION,
) -> None:
    """Play a role recording from an offset until the next silence."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    if _is_segment_id(target):
        player = SegmentAudioPlayer(paths=cfg)
        if player.play(target):
            return
        logging.info(
            "segment %s not found... have you run the 'segments' command?",
            target,
        )
        raise typer.Exit(code=1)
    checker = AudioCheck(base_dir=cfg.root.parent)
    raise SystemExit(checker.run(target, offset_ms, continue_play, offset_mod))


@whisper_app.command("whisper-init", hidden=True)
def whisper_init(
    model: list[str] = typer.Option(None, "--model", "-m", help="Whisper model name(s) to cache"),
    device: str = typer.Option("cpu", help="Device to load the model for caching"),
    compute_type: str = typer.Option("int8", help="Compute type for loading cached models"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Download and cache Whisper model weights for offline use."""
    cfg = paths.PathConfig(play or paths.default_play_name())
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
    logging.info("✅ cached whisper model(s) in %s", paths.display_path(store.cache_dir))


@app.command("audioplay", rich_help_panel="build")
def audioplay(
    target: str | None = typer.Argument(
        None,
        metavar="TARGET",
        help="Role name or segment id to play (segment ids look like 1_17_3)",
    ),
    part: str = typer.Option(None, help="Part number to assemble, '_' for preamble, omit for all parts"),
    segment_spacing_ms: int = typer.Option(SEGMENT_SPACING_MS, help="Silence (ms) to insert between segments"),
    callouts: bool = typer.Option(True, help="Prepend each role line with its callout audio"),
    callout_spacing_ms: int = typer.Option(CALLOUT_SPACING_MS, help="Silence (ms) between callout and line"),
    minimal_callouts: bool = typer.Option(False, help="Reduce callouts during alternating two-person dialogue"),
    captions: bool = typer.Option(True, help="Generate captions (WebVTT) and mux into mp4 when possible"),
    generate_audio: bool = typer.Option(True, help="Write rendered audio (disable to only emit audio_plan.txt)"),
    librivox: bool | None = typer.Option(None, "--librivox/--no-librivox", help="Generate Librivox-style mp3s (one per part, no prelude)"),
    audio_format: str = typer.Option("mp4", help="Output format: mp4 (default), mp3, or wav"),
    normalize_output: bool = typer.Option(True, help="Normalize the generated audioplay"),
    prepare: bool = typer.Option(True, help="Ensure text/scripts and split segments are up to date before building"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Assemble final audio play output for a part or full play."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    if target:
        play_obj = load_production_play(cfg)
        valid_roles = {r.name for r in play_obj.roles} | {"_NARRATOR", "_CALLER", "_ANNOUNCER"}
        if target not in valid_roles:
            if _is_segment_id(target):
                player = SegmentAudioPlayer(paths=cfg)
                if player.play(target):
                    return
                logging.info(
                    "segment %s not found... have you run the 'segments' command?",
                    target,
                )
                raise typer.Exit(code=1)
    with rich_progress() as progress:
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
            progress_reporter=RichProgressReporter(progress),
        )


@app.command("normalize", rich_help_panel="utility")
def normalize(
    src: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        help="Audio file to normalize",
    ),
    play: str | None = PLAY_OPTION,
) -> None:
    """
    Normalize an audio file using ffmpeg loudnorm. Writes to a sibling 'normalized' folder.
    """
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    result = run_normalize(src)
    typer.echo(result.render())


@app.command("cues", rich_help_panel="build")
def cues(
    role: str = typer.Option(None, help="Role to build cues for; default builds all roles"),
    response_delay_ms: int = typer.Option(2000, help="Silence (ms) between cue and response"),
    max_cue_size_ms: int = typer.Option(5000, help="Max cue length before cropping (ms)"),
    include_prompts: bool = typer.Option(True, help="Include preceding prompts; disables if set false"),
    callout_spacing_ms: int = typer.Option(300, help="Silence (ms) between prompt callout and prompt"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Generate cue audio snippets for roles."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    with rich_progress() as progress:
        run_cues(
            role=role,
            response_delay_ms=response_delay_ms,
            max_cue_size_ms=max_cue_size_ms,
            include_prompts=include_prompts,
            callout_spacing_ms=callout_spacing_ms,
            paths_config=cfg,
            progress_reporter=RichProgressReporter(progress),
        )


@app.command("playbook", rich_help_panel="build")
def playbook(
    librivox: bool | None = typer.Option(None, "--librivox/--no-librivox", help="Override configured build type metadata"),
    audio_format: str = typer.Option("wav", "--audio-format", help="Playbook audio format: wav or mp3"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Build a Cuemaster Playbook manifest and package."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    with rich_progress() as progress:
        run_playbook(
            paths_config=cfg,
            build_type=BuildTypeResolver(paths_config=cfg, librivox_override=librivox).resolve(),
            audio_format=audio_format,
            progress_reporter=RichPlaybookProgressReporter(progress),
        )


@app.command("recording-request", rich_help_panel="build")
def recording_request(
    role: str = typer.Option(..., "--role", "-r", help="Role to build a Recording Request for"),
    item: list[str] | None = typer.Option(
        None,
        "--item",
        "-i",
        help="Limit request to a recording item id such as 5-32:s1; repeat for multiple selected items",
    ),
    segment: list[str] | None = typer.Option(
        None,
        "--segment",
        help="Deprecated alias for --item; accepts old Stager segment ids or production recording item ids",
    ),
    reason: str | None = typer.Option(None, "--reason", help="Reason shown for selected recording items"),
    notes: str | None = typer.Option(None, "--notes", help="Optional request notes for the actor"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Build a LineRecorder Recording Request package."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    zip_path = run_recording_request(
        role=role,
        item_ids=selected_recording_item_ids(item, segment),
        item_reason=reason,
        notes=notes,
        paths_config=cfg,
    )
    typer.echo(paths.display_path(zip_path))


@app.command("recording-import", rich_help_panel="build")
def recording_import(
    package: Path = typer.Argument(..., help="LineRecorder role recordings zip to import"),
    denoise: bool = typer.Option(False, "--denoise", help="Use included floor-noise recordings for import-time denoising"),
    trim_silence: bool = typer.Option(False, "--trim-silence", help="Trim leading and trailing silence during import"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Import a LineRecorder role recordings package into Stager segments."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    result = run_recording_import(
        package_path=package,
        denoise=denoise,
        trim_silence=trim_silence,
        paths_config=cfg,
    )
    status = "complete" if result.complete else "partial"
    typer.echo(
        f"Imported {result.imported_count} {status} recordings for {result.role}"
        f" ({len(result.missing_segment_ids)} missing)"
    )
    for issue in result.issues:
        typer.echo(f"Warning [{issue.code}]: {issue.message}")
    typer.echo(paths.display_path(result.transaction_manifest_path))


@app.command("recording-import-undo", rich_help_panel="build")
def recording_import_undo(
    transaction: Path = typer.Argument(..., help="LineRecorder import transaction JSON to undo"),
    play: str | None = PLAY_OPTION,
) -> None:
    """Undo a LineRecorder import transaction."""
    cfg = paths.PathConfig(play or paths.default_play_name())
    setup_logging(cfg)
    result = run_recording_import_undo(transaction_path=transaction, paths_config=cfg)
    typer.echo(
        f"Undid import for {result.role}: restored {result.restored_count}, removed {result.removed_count}"
    )


# Helper functions (non-Typer) -----------------------------------------------

def run_text(
    line_no_prefix: bool = True,
    paths_config: paths.PathConfig | None = None,
    build_type: str | None = None,
) -> None:
    cfg = paths_config or paths.current()
    TextArtifactBuilder(paths=cfg).build_all(line_no_prefix=line_no_prefix, build_type=build_type)


def run_write_play(line_no_prefix: bool = True, paths_config: paths.PathConfig | None = None):
    cfg = paths_config or paths.current()
    return TextArtifactBuilder(paths=cfg).write_play(line_no_prefix=line_no_prefix)


def run_write_roles(line_no_prefix: bool = True, paths_config: paths.PathConfig | None = None):
    cfg = paths_config or paths.current()
    return TextArtifactBuilder(paths=cfg).write_roles(line_no_prefix=line_no_prefix)


def run_write_callout_script(paths_config: paths.PathConfig | None = None):
    cfg = paths_config or paths.current()
    return TextArtifactBuilder(paths=cfg).write_callout_script()

def run_write_announcer(
    paths_config: paths.PathConfig | None = None,
    build_type: str | None = None,
):
    cfg = paths_config or paths.current()
    return TextArtifactBuilder(paths=cfg).write_announcer(build_type=build_type)


def run_write_cues(paths_config: paths.PathConfig | None = None):
    from stager.cues.role_cues import RoleCues
    from stager.cues.narration_cues import NarrationCues

    cfg = paths_config or paths.current()
    play = load_production_play(cfg)
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
    build_type: str | None = None,
    progress_reporter: ProgressReporter | None = None,
):
    cfg = paths_config or paths.current()
    return SegmentBuildService(paths=cfg, progress_reporter=progress_reporter).build(
        role=role,
        part=part,
        silence_thresh=silence_thresh,
        separator_len_ms=separator_len_ms,
        chunk_size=chunk_size,
        verbose=verbose,
        chunk_exports=chunk_exports,
        chunk_export_size=chunk_export_size,
        force=force,
        build_type=build_type,
    )


def run_check_recording(paths_config: paths.PathConfig | None = None):
    cfg = paths_config or paths.current()
    for line in RecordingChecker(paths=cfg).summarize():
        typer.echo(line)


def run_generate_timings(
    librivox: bool | None,
    segment_spacing_ms: int = SEGMENT_SPACING_MS,
    callouts: bool = True,
    callout_spacing_ms: int = CALLOUT_SPACING_MS,
    minimal_callouts: bool = False,
    include_decorations: bool = True,
    paths_config: paths.PathConfig | None = None,
):
    cfg = paths_config or paths.current()
    TimingBuildService(paths=cfg).build(
        librivox=librivox,
        segment_spacing_ms=segment_spacing_ms,
        callouts=callouts,
        callout_spacing_ms=callout_spacing_ms,
        minimal_callouts=minimal_callouts,
        include_decorations=include_decorations,
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
    librivox: bool | None = None,
    audio_format: str = "mp4",
    normalize_output: bool = True,
    prepare: bool = True,
    paths_config: paths.PathConfig | None = None,
    progress_reporter: ProgressReporter | None = None,
):
    if audio_format not in ("mp4", "mp3", "wav"):
        raise typer.BadParameter("audio-format must be one of: mp4, mp3, wav")
    cfg = paths_config or paths.current()
    return AudioPlayBuildService(paths=cfg, progress_reporter=progress_reporter).build(
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
        prepare=prepare,
    )


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
    progress_reporter: ProgressReporter | None = None,
):
    cfg = paths_config or paths.current()
    CueBuildService(paths=cfg, progress_reporter=progress_reporter).build(
        role=role,
        response_delay_ms=response_delay_ms,
        max_cue_size_ms=max_cue_size_ms,
        include_prompts=include_prompts,
        callout_spacing_ms=callout_spacing_ms,
    )


def run_playbook(
    *,
    paths_config: paths.PathConfig | None = None,
    build_type: str | None = None,
    audio_format: str = "wav",
    progress_reporter: PlaybookProgressReporter | None = None,
) -> Path:
    if audio_format not in ("wav", "mp3"):
        raise typer.BadParameter("audio-format must be one of: wav, mp3")
    cfg = paths_config or paths.current()
    effective_build_type = BuildTypeResolver(
        paths_config=cfg,
        explicit_build_type=build_type,
    ).resolve()
    play = load_production_play(cfg)
    builder = PlaybookBuilder(
        play=play,
        paths=cfg,
        build_type=effective_build_type,
        audio_format=audio_format,
        progress_reporter=progress_reporter,
    )
    return builder.build()


def run_recording_request(
    *,
    role: str,
    item_ids: set[str] | None = None,
    item_reason: str | None = None,
    notes: str | None = None,
    paths_config: paths.PathConfig | None = None,
) -> Path:
    cfg = paths_config or paths.current()
    play = load_production_play(cfg)
    valid_roles = {candidate.name for candidate in play.roles if not candidate.meta and not candidate.name.startswith("_")}
    if role not in valid_roles:
        raise typer.BadParameter(f"Unknown rehearsable role: {role}")
    builder = RecordingRequestBuilder(
        play=play,
        paths=cfg,
        role=role,
        request_kind="selected_segments" if item_ids else "full_role",
        selected_segment_ids=item_ids,
        item_reason=item_reason,
        notes=notes,
    )
    return builder.build()


def selected_recording_item_ids(item_ids: list[str] | None, segment_ids: list[str] | None) -> set[str] | None:
    selected = [*(item_ids or []), *(segment_ids or [])]
    return set(selected) if selected else None


def run_recording_import(
    *,
    package_path: Path,
    denoise: bool = False,
    trim_silence: bool = False,
    paths_config: paths.PathConfig | None = None,
):
    cfg = paths_config or paths.current()
    play = load_production_play(cfg)
    return RoleRecordingsImporter(paths=cfg, play=play).import_package(
        package_path,
        processing_options=RecordingImportProcessingOptions(denoise=denoise, trim_silence=trim_silence),
    )


def run_recording_import_undo(
    *,
    transaction_path: Path,
    paths_config: paths.PathConfig | None = None,
):
    cfg = paths_config or paths.current()
    return RoleRecordingsImporter(paths=cfg).undo_import(transaction_path)


def _is_segment_id(value: str) -> bool:
    parts = value.split("_")
    if len(parts) != 3:
        return False
    return all(part.isdigit() for part in parts)



def main() -> None:
    if len(sys.argv) == 2:
        # If only one argument string is passed (e.g., from VSCode or manual entry)
        preprocessed_args = shlex.split(sys.argv[1])
        sys.argv = [sys.argv[0]] + preprocessed_args
    app()


if __name__ == "__main__":
    main()
