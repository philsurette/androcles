from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

from pydub import AudioSegment

from stager.playbook.app_cue_start_offset import AppCueStartOffset
from stager.playbook.cue_window_presets import CueWindowPresets


@dataclass
class CueStartOffsetAnalyzer:
    windows_ms: list[int] = field(
        default_factory=lambda: CueWindowPresets().timed_windows_ms()
    )
    search_radius_ms: int = 1500
    rms_window_ms: int = 40
    hop_ms: int = 20
    quiet_ratio: float = 0.35

    def analyze(self, audio_path: Path, duration_ms: int) -> list[AppCueStartOffset]:
        if audio_path.suffix.lower() != ".wav":
            return []
        audio = AudioSegment.from_file(audio_path).set_channels(1)
        return [
            self._offset_for_window(audio, duration_ms, window_ms)
            for window_ms in self.windows_ms
        ]

    def _offset_for_window(
        self,
        audio: AudioSegment,
        duration_ms: int,
        requested_window_ms: int,
    ) -> AppCueStartOffset:
        target_start_ms = max(0, duration_ms - requested_window_ms)
        if target_start_ms == 0:
            return AppCueStartOffset(
                requested_window_ms=requested_window_ms,
                start_ms=0,
                confidence="exact",
            )

        search_start_ms = max(0, target_start_ms - self.search_radius_ms)
        search_end_ms = min(duration_ms, target_start_ms + self.search_radius_ms)
        boundary_ms = self._best_boundary(
            audio,
            search_start_ms,
            search_end_ms,
            target_start_ms,
        )
        if boundary_ms is None:
            return AppCueStartOffset(
                requested_window_ms=requested_window_ms,
                start_ms=target_start_ms,
                confidence="fallback",
            )
        return AppCueStartOffset(
            requested_window_ms=requested_window_ms,
            start_ms=boundary_ms,
            confidence="boundary",
        )

    def _best_boundary(
        self,
        audio: AudioSegment,
        search_start_ms: int,
        search_end_ms: int,
        target_start_ms: int,
    ) -> int | None:
        samples = self._smoothed_rms_samples(audio, search_start_ms, search_end_ms)
        if not samples:
            return None

        threshold = max(1.0, median(rms for _, rms in samples) * self.quiet_ratio)
        candidates = [(position, rms) for position, rms in samples if rms <= threshold]
        if not candidates:
            return None

        return min(
            candidates,
            key=lambda sample: (
                sample[1],
                abs(sample[0] - target_start_ms),
                0 if sample[0] <= target_start_ms else 1,
            ),
        )[0]

    def _smoothed_rms_samples(
        self,
        audio: AudioSegment,
        search_start_ms: int,
        search_end_ms: int,
    ) -> list[tuple[int, float]]:
        raw_samples: list[tuple[int, int]] = []
        for position_ms in range(search_start_ms, search_end_ms, self.hop_ms):
            end_ms = min(position_ms + self.rms_window_ms, search_end_ms)
            if end_ms <= position_ms:
                continue
            raw_samples.append((position_ms, audio[position_ms:end_ms].rms))

        smoothed: list[tuple[int, float]] = []
        for index, (position_ms, rms) in enumerate(raw_samples):
            nearby = [rms]
            if index > 0:
                nearby.append(raw_samples[index - 1][1])
            if index + 1 < len(raw_samples):
                nearby.append(raw_samples[index + 1][1])
            smoothed.append((position_ms, sum(nearby) / len(nearby)))
        return smoothed
