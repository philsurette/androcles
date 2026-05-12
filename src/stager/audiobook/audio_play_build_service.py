"""Service for building assembled audioplay output."""
from __future__ import annotations

from dataclasses import dataclass
import logging

from stager.audio.segment_build_service import SegmentBuildService
from stager.audiobook.play_builder import PlayBuilder
from stager.domain.play import Play
from stager.loudnorm.normalizer import Normalizer
from stager.scriptwright.production_play_loader import ProductionPlayLoader
from stager.shared import paths as path_display
from stager.shared.build_type_resolver import BuildTypeResolver
from stager.shared.paths import PathConfig
from stager.text.text_artifact_builder import TextArtifactBuilder


logger = logging.getLogger(__name__)


@dataclass
class AudioPlayBuildService:
    """Build audioplay media and optional normalized copies."""

    paths: PathConfig

    def build(
        self,
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
    ):
        effective_build_type = BuildTypeResolver(
            paths_config=self.paths,
            librivox_override=librivox,
        ).resolve()
        effective_librivox = effective_build_type == "librivox"
        if prepare:
            logger.info("Preparing text artifacts and split segments before audioplay")
            TextArtifactBuilder(paths=self.paths).build_all(line_no_prefix=True, build_type=effective_build_type)
            SegmentBuildService(paths=self.paths).build(build_type=effective_build_type)
        play: Play = ProductionPlayLoader(paths_config=self.paths).load()
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
            librivox=effective_librivox,
            play=play,
            paths=self.paths,
        )
        out_paths = builder.build_audio(part_no=part_no)
        if normalize_output and generate_audio:
            normalizer = Normalizer()
            for out_path in out_paths:
                target_dir = out_path.parent / "normalized"
                target_dir.mkdir(parents=True, exist_ok=True)
                norm_path = target_dir / out_path.name
                logger.info("Normalizing audioplay to %s", path_display.display_path(norm_path))
                normalizer.normalize(str(out_path), str(norm_path))
        elif normalize_output and not generate_audio:
            logger.info("Skipping normalization because audio rendering was skipped.")
        return out_paths
