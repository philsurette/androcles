#!/usr/bin/env python3
"""Utilities for mixing audio clips together (parallel playback)."""
from __future__ import annotations

from dataclasses import dataclass, field
import subprocess
import tempfile
import math
from pathlib import Path
from typing import Iterable, List

from pydub import AudioSegment
from abc import ABC, abstractmethod


class MixAttenuator(ABC):
    @abstractmethod
    def attenuation_db(self, num_tracks: int):
        raise NotImplementedError
    
@dataclass
class PerceptualSummationAttenuator(MixAttenuator):
    scale_down: float = field(default=0.6)  # fraction of full volume-preserving attenuation
    def attenuation_db(self, num_tracks: int):
        return self.scale_down * 10.0 * math.log10(num_tracks)
    
class DirectSummationAttenuator(MixAttenuator):
    def attenuation_db(self, num_tracks: int):
        return 0
    
class VolumePreservingAttenuator(MixAttenuator):
    """
    Full "volume-preserving" (power-compensating) attenuation.

    If n similar, mostly-uncorrelated tracks are summed, total power ~ n.
    To keep the mix at roughly the same loudness as a single track, attenuate
    each track by 10*log10(n) dB.
    """
    def attenuation_db(self, num_tracks: int):
        return 10.0 * math.log10(num_tracks)

@dataclass
class AudioMixer:
    """Mix multiple audio files together using ffmpeg."""
    attenuator: MixAttenuator = field(default_factory=PerceptualSummationAttenuator)

    def mix_parallel(self, paths: Iterable[Path]) -> AudioSegment | None:
        """
        Return an AudioSegment with all paths mixed together
        """
        inputs: List[Path] = [p for p in paths if p and Path(p).exists()]

        if len(inputs) == 1:
            return AudioSegment.from_file(inputs[0])

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_out = Path(tmpdir) / "mix.wav"
            cmd = ["ffmpeg", "-y"]
            for p in inputs:
                cmd.extend(["-i", str(p)])
            n = len(inputs)
            attenuation_db = self.attenuator.attenuation_db(n)
            filters: List[str] = []
            stream_labels: List[str] = []
            for idx in range(n):
                in_label = f"{idx}:a"
                out_label = f"a{idx}"
                if attenuation_db > 0:
                    filters.append(f"[{in_label}]volume={-attenuation_db}dB[{out_label}]")
                else:
                    filters.append(f"[{in_label}]anull[{out_label}]")
                stream_labels.append(f"[{out_label}]")
            filters.append(
                "".join(stream_labels)
                + f"amix=inputs={n}:duration=longest:dropout_transition=0[mix]"
            )
            filter_arg = ";".join(filters)
            cmd.extend(["-filter_complex", filter_arg, "-map", "[mix]", str(tmp_out)])
            subprocess.run(cmd, check=True)
            return AudioSegment.from_file(tmp_out)
