"""Service for splitting play recordings into segment audio."""
from __future__ import annotations

from dataclasses import dataclass

from stager.audio.audacity_recording_exporter import AudacityRecordingExporter
from stager.audio.play_splitter import PlaySplitter
from stager.shared.build_type_resolver import BuildTypeResolver
from stager.shared.paths import PathConfig
from stager.shared.progress_reporter import ProgressReporter
from stager.scriptwright.production_play_loader import ProductionPlayLoader


@dataclass
class SegmentBuildService:
    """Build segment audio files from exported role recordings."""

    paths: PathConfig
    progress_reporter: ProgressReporter | None = None

    def build(
        self,
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
        build_type: str | None = None,
    ):
        effective_build_type = BuildTypeResolver(
            paths_config=self.paths,
            explicit_build_type=build_type,
        ).resolve()
        play = ProductionPlayLoader(paths_config=self.paths).load()
        if self.progress_reporter is not None:
            split_target_count = PlaySplitter(
                play=play,
                paths=self.paths,
                build_type=effective_build_type,
            ).split_target_count(role_filter=role)
            self.progress_reporter.start(split_target_count + 1, "Exporting recordings")
        AudacityRecordingExporter(paths=self.paths).export_recordings(force=force, role=role)
        if self.progress_reporter is not None:
            self.progress_reporter.advance("Splitting segments")
        splitter = PlaySplitter(
            play=play,
            paths=self.paths,
            build_type=effective_build_type,
            force=force,
            min_silence_ms=separator_len_ms,
            silence_thresh=silence_thresh,
            chunk_size=chunk_size,
            verbose=verbose,
            chunk_exports=chunk_exports,
            chunk_export_size=chunk_export_size,
            progress_reporter=self.progress_reporter,
        )
        result = splitter.split_all(part_filter=part, role_filter=role)
        if self.progress_reporter is not None:
            self.progress_reporter.finish("Split segments")
        return result
