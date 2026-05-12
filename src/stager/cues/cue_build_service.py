"""Service for generating legacy cue audio files."""
from __future__ import annotations

from dataclasses import dataclass

from stager.cues.cue_builder import CueBuilder
from stager.scriptwright.production_play_loader import ProductionPlayLoader
from stager.shared.paths import PathConfig
from stager.shared.progress_reporter import ProgressReporter


@dataclass
class CueBuildService:
    """Build cue files for one role or all rehearsal roles."""

    paths: PathConfig
    progress_reporter: ProgressReporter | None = None

    def build(
        self,
        *,
        role: str | None = None,
        response_delay_ms: int = 2000,
        max_cue_size_ms: int = 5000,
        include_prompts: bool = True,
        callout_spacing_ms: int = 300,
    ) -> None:
        play = ProductionPlayLoader(paths_config=self.paths).load()
        builder = CueBuilder(
            play,
            paths=self.paths,
            response_delay_ms=response_delay_ms,
            max_cue_size_ms=max_cue_size_ms,
            include_prompts=include_prompts,
            callout_spacing_ms=callout_spacing_ms,
        )
        roles = [role] if role else [r.name for r in play.roles] + ["_NARRATOR"]
        if self.progress_reporter is not None:
            self.progress_reporter.start(len(roles), "Building cue files")
        for role_name in roles:
            builder.build_cues(role_name)
            if self.progress_reporter is not None:
                self.progress_reporter.advance(f"Built cues for {role_name}")
        if self.progress_reporter is not None:
            self.progress_reporter.finish("Built cue files")
