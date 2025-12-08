#!/usr/bin/env python3
"""Thin wrapper to build audio plans and optionally render them."""
from __future__ import annotations

import logging
from pathlib import Path
from dataclasses import dataclass, field

from play_plan_builder import PlayPlanBuilder, write_plan, PlanItem
from play_text import PlayTextParser, PlayText, Part
from chapter_builder import ChapterBuilder
from callout_director import CalloutDirector, ConversationAwareCalloutDirector, RoleCalloutDirector, NoCalloutDirector
from play_audio_builder import instantiate_plan
from caption_builder import CaptionBuilder
import paths


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
    play: PlayText = None

    def build_audio(self, part_no: int) -> list[Path]:
        """Build audio plans (and optional outputs) using configured settings."""
        # self.play = PlayTextParser().parse()
        if self.librivox:
            return self._build_librivox()

        out_path = self.compute_output_path(part_no, self.audio_format)
        chapters = ChapterBuilder().build()
        director: CalloutDirector = (
            ConversationAwareCalloutDirector(self.play) if self.minimal_callouts else RoleCalloutDirector(self.play)
        )
        director = director if self.include_callouts else NoCalloutDirector(self.play)
        builder = PlayPlanBuilder(
            play=self.play,
            director=director,
            chapters=chapters,
            spacing_ms=self.spacing_ms,
            include_callouts=self.include_callouts,
            callout_spacing_ms=self.callout_spacing_ms,
            minimal_callouts=self.minimal_callouts,
            part_gap_ms=self.part_gap_ms,
            librivox=self.librivox,
        )
        plan = builder.build_audio_plan(part_no=part_no)
        plan_path = paths.BUILD_DIR / "audio_plan.txt"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        write_plan(plan, plan_path)
        logging.info("Wrote audio plan to %s", plan_path)
        captions_path: Path | None = None
        if self.generate_captions:
            captions_path = paths.BUILD_DIR / "captions.vtt"
            CaptionBuilder(plan, include_callouts=self.include_callouts).build(captions_path)
            logging.info("Wrote captions to %s", captions_path)
        if self.generate_audio:
            logging.info("Generating audioplay to %s", out_path)
            instantiate_plan(plan, out_path, audio_format=self.audio_format, captions_path=captions_path)
            logging.info("Wrote %s", out_path)
        else:
            logging.info("Skipping audio rendering (generate-audio=false)")
        return [out_path]

    def compute_output_path(self, part_no: int, audio_format: str = "mp4") -> Path:
        if part_no is None:
            title = "play"
        else:
            part: Part = self.play.getPart(part_no=part_no)
            title = f"{part.part_no}_{part.title}"
        return paths.AUDIO_PLAY_DIR / f"{title}.{audio_format}"

    def _build_librivox(self) -> list[Path]:
        outputs: list[Path] = []
        chapters = ChapterBuilder(play_text=self.play).build()
        director: CalloutDirector = (
            ConversationAwareCalloutDirector(self.play) if self.minimal_callouts else RoleCalloutDirector(self.play)
        )
        director = director if self.include_callouts else NoCalloutDirector(self.play)
        file_friendly_title = ''.join(self.play.title.lower().split())
        for part_no in [p.part_no for p in self.play.parts if p.part_no is not None]:
            out_path = paths.AUDIO_PLAY_DIR / f"{file_friendly_title}_{part_no}_shaw_128kb.mp3"
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
                spacing_ms=self.spacing_ms,
                include_callouts=self.include_callouts,
                callout_spacing_ms=self.callout_spacing_ms,
                part_gap_ms=0,
                librivox=True,
            )
            plan = builder.build_audio_plan(part_no=part_no)
            plan = [item for item in plan if item.__class__.__name__ != "Chapter"]
            plan_path = paths.BUILD_DIR / f"audio_plan_part_{part_no}.txt"
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            write_plan(plan, plan_path)
            logging.info("Wrote audio plan to %s", plan_path)
            if self.generate_audio:
                instantiate_plan(
                    plan,
                    out_path,
                    audio_format="mp3",
                    captions_path=None,
                    prepend_paths=[],
                    append_paths=[],
                    metadata=metadata,
                )
                logging.info("Wrote %s", out_path)
            else:
                logging.info("Skipping audio rendering (generate-audio=false)")
        return outputs


__all__ = ["PlayBuilder", "PlanItem"]
