#!/usr/bin/env python3
"""Thin wrapper to build audio plans and optionally render them."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from play_plan_builder import (
    build_audio_plan,
    compute_output_path,
    list_parts,
    write_plan,
    PlanItem,
)
from play_audio_builder import instantiate_plan
from caption_builder import build_captions
from paths import BUILD_DIR, RECORDINGS_DIR, AUDIO_PLAY_DIR


def build_audio(
    parts: List[int | None],
    part: int | None = None,
    spacing_ms: int = 0,
    include_callouts: bool = False,
    callout_spacing_ms: int = 300,
    minimal_callouts: bool = False,
    audio_format: str = "mp4",
    part_gap_ms: int = 0,
    generate_audio: bool = True,
    generate_captions: bool = True,
    librivox: bool = False,
) -> List[Path]:
    if librivox:
        parts_numeric = [p for p in parts if p is not None]
        if not parts_numeric:
            raise ValueError("No numbered parts available for librivox output.")
        outputs: List[Path] = []
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
            plan, _ = build_audio_plan(
                parts=[part_id],
                spacing_ms=spacing_ms,
                include_callouts=include_callouts,
                callout_spacing_ms=callout_spacing_ms,
                minimal_callouts=minimal_callouts,
                part_gap_ms=0,
                part_index_offset=idx,
                total_parts=len(parts_numeric),
                librivox=True,
            )
            plan = [item for item in plan if item.__class__.__name__ != "Chapter"]
            plan_path = BUILD_DIR / f"audio_plan_part_{part_id}.txt"
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            write_plan(plan, plan_path)
            logging.info("Wrote audio plan to %s", plan_path)
            if generate_audio:
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

    out_path = compute_output_path(parts, part, audio_format)
    plan, _ = build_audio_plan(
        parts=parts,
        spacing_ms=spacing_ms,
        include_callouts=include_callouts,
        callout_spacing_ms=callout_spacing_ms,
        minimal_callouts=minimal_callouts,
        part_gap_ms=part_gap_ms,
        librivox=librivox,
    )
    plan_path = BUILD_DIR / "audio_plan.txt"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    write_plan(plan, plan_path)
    logging.info("Wrote audio plan to %s", plan_path)
    captions_path: Path | None = None
    if generate_captions:
        captions_path = BUILD_DIR / "captions.vtt"
        build_captions(plan, captions_path, include_callouts=include_callouts)
        logging.info("Wrote captions to %s", captions_path)
    if generate_audio:
        logging.info("Generating audioplay to %s", out_path)
        instantiate_plan(plan, out_path, audio_format=audio_format, captions_path=captions_path)
        logging.info("Wrote %s", out_path)
    else:
        logging.info("Skipping audio rendering (generate-audio=false)")
    return [out_path]


__all__ = ["build_audio", "compute_output_path", "list_parts", "PlanItem"]
