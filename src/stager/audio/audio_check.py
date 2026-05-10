#!/usr/bin/env python3
"""Play a role recording from an offset until the next silence."""
from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
import re
import subprocess

from stager.shared.play_config import PlayConfig
from stager.shared import paths


@dataclass
class AudioCheck:
    base_dir: Path
    min_silence_ms: int = 1500
    silence_db: float = -35.0
    _silence_start_re: re.Pattern[str] = field(
        default_factory=lambda: re.compile(r"silence_start:\s*(\d+(?:\.\d+)?)")
    )

    def run(
        self,
        role: str,
        offset_ms: int,
        continue_play: bool,
        offset_mod: float,
    ) -> int:
        if offset_ms < 0:
            raise RuntimeError("Offset must be a non-negative integer (ms)")
        offset_mod_ms = int(round(offset_mod * 1000))
        start_ms = max(0, offset_ms + offset_mod_ms)
        start_seconds = start_ms / 1000.0
        config = PlayConfig.load(self.base_dir)
        audio_path = (
            self.base_dir
            / "plays"
            / config.play_id
            / "recordings"
            / f"{role}.wav"
        )
        if not audio_path.exists():
            raise RuntimeError(f"Recording not found: {paths.display_path(audio_path)}")
        stop_ms = None
        if not continue_play:
            silence_start = self._find_silence_start(audio_path, start_seconds)
            if silence_start is not None:
                stop_ms = start_ms + int(round(silence_start * 1000)) + 1000
        logging.info(
            "Starting ffplay for %s at %dms%s",
            paths.display_path(audio_path),
            start_ms,
            "" if stop_ms is None else f" (stops at {stop_ms}ms)",
        )
        command = [
            "ffplay",
            "-nodisp",
            "-loglevel",
            "error",
            "-ss",
            f"{start_seconds:.3f}",
        ]
        if stop_ms is not None:
            duration_ms = max(0, stop_ms - start_ms)
            duration_seconds = duration_ms / 1000.0
            command.extend(["-t", f"{duration_seconds:.3f}", "-autoexit"])
        else:
            command.append("-autoexit")
        command.extend(["-i", str(audio_path)])
        return subprocess.call(command)

    def _find_silence_start(self, audio_path: Path, start_seconds: float) -> float | None:
        duration_seconds = self.min_silence_ms / 1000.0
        filter_arg = f"silencedetect=noise={self.silence_db}dB:d={duration_seconds:.3f}"
        command = [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "info",
            "-ss",
            f"{start_seconds:.3f}",
            "-i",
            str(audio_path),
            "-af",
            filter_arg,
            "-f",
            "null",
            "-",
        ]
        proc = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        silence_start = None
        if proc.stderr is None:
            raise RuntimeError("Failed to read ffmpeg output")
        for line in proc.stderr:
            match = self._silence_start_re.search(line)
            if not match:
                continue
            silence_start = float(match.group(1))
            break
        if silence_start is not None:
            proc.terminate()
        proc.wait()
        return silence_start
