#!/usr/bin/env python3
"""Play a split segment audio file by segment id."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import subprocess

from stager.shared import paths


@dataclass
class SegmentAudioPlayer:
    paths: paths.PathConfig

    def play(self, segment_id: str) -> bool:
        path = self._find_segment_path(segment_id)
        if path is None:
            return False
        logging.info("Playing segment %s (%s)", segment_id, paths.display_path(path))
        return_code = subprocess.call(
            [
                "ffplay",
                "-nodisp",
                "-autoexit",
                "-loglevel",
                "error",
                "-i",
                str(path),
            ]
        )
        if return_code != 0:
            raise RuntimeError(f"ffplay failed with code {return_code}")
        return True

    def _find_segment_path(self, segment_id: str) -> Path | None:
        segments_dir = self.paths.segments_dir
        if not segments_dir.exists():
            return None
        candidate_name = f"{segment_id}.wav"
        for role_dir in segments_dir.iterdir():
            if not role_dir.is_dir():
                continue
            candidate = role_dir / candidate_name
            if candidate.exists():
                return candidate
        return None
