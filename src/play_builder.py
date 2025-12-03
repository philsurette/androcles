#!/usr/bin/env python3
"""Thin wrapper to build audio plans and optionally render them."""
from __future__ import annotations

import logging
from pathlib import Path
from dataclasses import dataclass

from play_plan_builder import PlayPlanBuilder, compute_output_path, list_parts, write_plan, PlanItem
from play_text import PlayTextParser
from chapter_builder import ChapterBuilder
from callout_director import CalloutDirector, ConversationAwareCalloutDirector, RoleCalloutDirector, NoCalloutDirector
from play_audio_builder import instantiate_plan
from caption_builder import CaptionBuilder
from paths import BUILD_DIR, RECORDINGS_DIR, AUDIO_PLAY_DIR


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

    def build_audio(self, parts: list[int | None], part: int | None = None) -> list[Path]:
        """Build audio plans (and optional outputs) using configured settings."""
        if self.librivox:
            return self._build_librivox(parts)

        out_path = compute_output_path(parts, part, self.audio_format)
        play = PlayTextParser().parse()
        chapters = ChapterBuilder().build()
        director: CalloutDirector = (
            ConversationAwareCalloutDirector(play) if self.minimal_callouts else RoleCalloutDirector(play)
        )
        director = director if self.include_callouts else NoCalloutDirector(play)
        builder = PlayPlanBuilder(
            play=play,
            director=director,
            chapters=chapters,
            spacing_ms=self.spacing_ms,
            include_callouts=self.include_callouts,
            callout_spacing_ms=self.callout_spacing_ms,
            minimal_callouts=self.minimal_callouts,
            part_gap_ms=self.part_gap_ms,
            librivox=self.librivox,
        )
        plan, _ = builder.build_audio_plan(parts=parts)
        plan_path = BUILD_DIR / "audio_plan.txt"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        write_plan(plan, plan_path)
        logging.info("Wrote audio plan to %s", plan_path)
        captions_path: Path | None = None
        if self.generate_captions:
            captions_path = BUILD_DIR / "captions.vtt"
            CaptionBuilder(plan, include_callouts=self.include_callouts).build(captions_path)
            logging.info("Wrote captions to %s", captions_path)
        if self.generate_audio:
            logging.info("Generating audioplay to %s", out_path)
            instantiate_plan(plan, out_path, audio_format=self.audio_format, captions_path=captions_path)
            logging.info("Wrote %s", out_path)
        else:
            logging.info("Skipping audio rendering (generate-audio=false)")
        return [out_path]

    def _build_librivox(self, parts: list[int | None]) -> list[Path]:
        parts_numeric = [p for p in parts if p is not None]
        if not parts_numeric:
            raise ValueError("No numbered parts available for librivox output.")
        outputs: list[Path] = []
        play = PlayTextParser().parse()
        chapters = ChapterBuilder(play_text=play).build()
        director: CalloutDirector = (
            ConversationAwareCalloutDirector(play) if self.minimal_callouts else RoleCalloutDirector(play)
        )
        director = director if self.include_callouts else NoCalloutDirector(play)
        for idx, part_id in enumerate(parts_numeric):
            out_path = AUDIO_PLAY_DIR / f"androclesandthelion_{part_id}_shaw_128kb.mp3"
            outputs.append(out_path)
            title_map = {0: "PROLOGUE", 1: "ACT I", 2: "ACT II"}
            metadata = {
                "title": title_map.get(part_id, str(part_id)),
                "artist": "LibriVox Volunteers",
                "album": "Androcles and the Lion",
                "track": f"{idx:02d}",
                "genre": "Speech",
            }
            builder = PlayPlanBuilder(
                play=play,
                director=director,
                chapters=chapters,
                spacing_ms=self.spacing_ms,
                include_callouts=self.include_callouts,
                callout_spacing_ms=self.callout_spacing_ms,
                part_gap_ms=0,
                librivox=True,
            )
            plan, _ = builder.build_audio_plan(parts=[part_id], part_index_offset=idx, total_parts=len(parts_numeric))
            plan = [item for item in plan if item.__class__.__name__ != "Chapter"]
            plan_path = BUILD_DIR / f"audio_plan_part_{part_id}.txt"
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


__all__ = ["PlayBuilder", "compute_output_path", "list_parts", "PlanItem"]
