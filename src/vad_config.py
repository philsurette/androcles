#!/usr/bin/env python3
"""Configuration for Silero VAD used by faster-whisper."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass
class VadConfig:
    """Silero VAD overrides for faster-whisper.

    Attributes:
        threshold: Speech probability threshold; higher values are more selective.
        neg_threshold: Silence threshold for ending speech; None derives from threshold.
        min_speech_duration_ms: Drop speech chunks shorter than this duration.
        max_speech_duration_s: Split speech chunks longer than this duration.
        min_silence_duration_ms: Required silence before splitting speech chunks.
        speech_pad_ms: Padding added to each side of detected speech chunks.
    """

    threshold: float | None = None
    neg_threshold: float | None = None
    min_speech_duration_ms: int | None = None
    max_speech_duration_s: float | None = None
    min_silence_duration_ms: int | None = None
    speech_pad_ms: int | None = None

    _default_threshold: ClassVar[float] = 0.5
    _default_min_speech_duration_ms: ClassVar[int] = 0
    _default_min_silence_duration_ms: ClassVar[int] = 160
    _default_speech_pad_ms: ClassVar[int] = 400

    @classmethod
    def from_overrides(
        cls,
        threshold: float | None = None,
        neg_threshold: float | None = None,
        min_speech_duration_ms: int | None = None,
        max_speech_duration_s: float | None = None,
        min_silence_duration_ms: int | None = None,
        speech_pad_ms: int | None = None,
    ) -> VadConfig | None:
        if (
            threshold is None
            and neg_threshold is None
            and min_speech_duration_ms is None
            and max_speech_duration_s is None
            and min_silence_duration_ms is None
            and speech_pad_ms is None
        ):
            return None
        return cls(
            threshold=threshold,
            neg_threshold=neg_threshold,
            min_speech_duration_ms=min_speech_duration_ms,
            max_speech_duration_s=max_speech_duration_s,
            min_silence_duration_ms=min_silence_duration_ms,
            speech_pad_ms=speech_pad_ms,
        )

    def to_transcribe_parameters(self) -> dict[str, float | int | None] | None:
        if not self._has_overrides():
            return None
        params: dict[str, float | int | None] = {
            "threshold": self.threshold
            if self.threshold is not None
            else self._default_threshold,
            "neg_threshold": self.neg_threshold,
            "min_speech_duration_ms": self.min_speech_duration_ms
            if self.min_speech_duration_ms is not None
            else self._default_min_speech_duration_ms,
            "min_silence_duration_ms": self.min_silence_duration_ms
            if self.min_silence_duration_ms is not None
            else self._default_min_silence_duration_ms,
            "speech_pad_ms": self.speech_pad_ms
            if self.speech_pad_ms is not None
            else self._default_speech_pad_ms,
        }
        if self.max_speech_duration_s is not None:
            params["max_speech_duration_s"] = self.max_speech_duration_s
        return params

    def _has_overrides(self) -> bool:
        return any(
            value is not None
            for value in (
                self.threshold,
                self.neg_threshold,
                self.min_speech_duration_ms,
                self.max_speech_duration_s,
                self.min_silence_duration_ms,
                self.speech_pad_ms,
            )
        )
