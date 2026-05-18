#!/usr/bin/env python3
"""Thin wrapper to build audio plans and optionally render them."""
from __future__ import annotations

import logging
from pathlib import Path
from dataclasses import dataclass, field

from stager.audiobook.play_plan_builder import PlayPlanBuilder, write_plan, PlanItem
from stager.domain.play import Play, Part
from stager.audiobook.chapter_builder import ChapterBuilder
from stager.cues.callout_director import CalloutDirector, ConversationAwareCalloutDirector, RoleCalloutDirector, NoCalloutDirector
from stager.audiobook.play_audio_builder import PlayAudioBuilder
from stager.audiobook.caption_builder import CaptionBuilder
from stager.shared import paths
from stager.shared.progress_reporter import ProgressReporter


@dataclass
class PlayBuilder:
    spacing_ms: int = 0
    include_callouts: bool = False
    callout_spacing_ms: int = 300
    minimal_callouts: bool = False
    audio_format: str = "mp4"
    part_gap_ms: int = 0
    generate_audio: bool = True
    generate_captions: bool = True
    librivox: bool = False
    use_cleaned_audio: bool = False
    play: Play = None
    paths: paths.PathConfig = field(default_factory=paths.current)
    audio_builder:PlayAudioBuilder = field(default_factory = PlayAudioBuilder)
    progress_reporter: ProgressReporter | None = None

    def build_audio(self, part_no: int) -> list[Path]:
        """Build audio plans (and optional outputs) using configured settings."""
        if self.librivox:
            return self._build_librivox()

        out_path = self.compute_output_path(part_no, self.audio_format)
        chapters = ChapterBuilder(play=self.play).build()
        director: CalloutDirector = (
            ConversationAwareCalloutDirector(self.play, paths_config=self.paths) if self.minimal_callouts else RoleCalloutDirector(self.play, paths_config=self.paths)
        )
        director = director if self.include_callouts else NoCalloutDirector(self.play)
        audio_builder = PlayAudioBuilder()
        builder = PlayPlanBuilder(
            play=self.play,
            director=director,
            chapters=chapters,
            paths=self.paths,
            segment_spacing_ms=self.spacing_ms,
            include_callouts=self.include_callouts,
            callout_spacing_ms=self.callout_spacing_ms,
            minimal_callouts=self.minimal_callouts,
            part_gap_ms=self.part_gap_ms,
            librivox=self.librivox,
            use_cleaned_audio=self.use_cleaned_audio,
        )
        plan = builder.build_audio_plan(part_no=part_no)
        plan_path = self.paths.build_dir / "audio_plan.txt"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        write_plan(plan, plan_path)
        logging.info("Wrote audio plan to %s", paths.display_path(plan_path))
        captions_path: Path | None = None
        if self.generate_captions:
            captions_path = self.paths.build_dir / "captions.vtt"
            CaptionBuilder(plan, include_callouts=self.include_callouts).build(captions_path)
            logging.info("Wrote captions to %s", paths.display_path(captions_path))
        if self.generate_audio:
            logging.info("Generating audioplay to %s", paths.display_path(out_path))
            audio_builder.instantiate_plan(plan, out_path, audio_format=self.audio_format, captions_path=captions_path)
            logging.info("Wrote %s", paths.display_path(out_path))
        else:
            logging.info("Skipping audio rendering (generate-audio=false)")
        if self.progress_reporter is not None:
            self.progress_reporter.advance(f"Rendered {out_path.name}")
        return [out_path]

    def compute_output_path(self, part_no: int, audio_format: str = "mp4") -> Path:
        if part_no is None:
            title = "play"
        else:
            part: Part = self.play.getPart(part_no=part_no)
            title = f"{part.part_no}_{part.title}"
        return self.paths.audio_play_dir / f"{title}.{audio_format}"

    def _build_librivox(self) -> list[Path]:
        outputs: list[Path] = []
        chapters = ChapterBuilder(play=self.play).build()
        director: CalloutDirector = (
            ConversationAwareCalloutDirector(self.play, paths_config=self.paths) if self.minimal_callouts else RoleCalloutDirector(self.play, paths_config=self.paths)
        )
        director = director if self.include_callouts else NoCalloutDirector(self.play)

        file_friendly_title = ''.join(self.play.title.lower().split())
        for part_no in [p.part_no for p in self.play.parts if p.part_no is not None]:
            out_path = self.paths.audio_play_dir / f"{file_friendly_title}_{part_no}_shaw_128kb.mp3"
            outputs.append(out_path)
            title_map = {0: "PROLOGUE", 1: "ACT I", 2: "ACT II"}
            metadata = {
                "title": title_map.get(part_no, str(part_no)),
                "artist": "LibriVox Volunteers",
                "album": "Androcles and the Lion",
                "track": f"{part_no:02d}",
                "genre": "Speech",
            }
            builder = PlayPlanBuilder(
                play=self.play,
                director=director,
                chapters=chapters,
                paths=self.paths,
                segment_spacing_ms=self.spacing_ms,
                include_callouts=self.include_callouts,
                callout_spacing_ms=self.callout_spacing_ms,
                part_gap_ms=0,
                librivox=True,
                use_cleaned_audio=self.use_cleaned_audio,
            )
            plan = builder.build_audio_plan(part_no=part_no)
            plan = [item for item in plan if item.__class__.__name__ != "Chapter"]
            plan_path = self.paths.build_dir / f"audio_plan_part_{part_no}.txt"
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            write_plan(plan, plan_path)
            logging.info("Wrote audio plan to %s", paths.display_path(plan_path))
            if self.generate_audio:
                self.audio_builder.instantiate_plan(
                    plan,
                    out_path,
                    audio_format="mp3",
                    captions_path=None,
                    prepend_paths=[],
                    append_paths=[],
                    metadata=metadata,
                )
                logging.info("Wrote %s", paths.display_path(out_path))
            else:
                logging.info("Skipping audio rendering (generate-audio=false)")
            if self.progress_reporter is not None:
                self.progress_reporter.advance(f"Rendered {out_path.name}")
        return outputs


__all__ = ["PlayBuilder", "PlanItem"]
