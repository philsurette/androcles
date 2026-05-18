from __future__ import annotations

import math
from dataclasses import dataclass

from stager.audio.voice_profile_config import (
    PITCH_STRATEGY_AUTO,
    PITCH_STRATEGY_LINKED_SPEED,
    PITCH_STRATEGY_PRESERVE_TEMPO,
    VoiceTransform,
)


@dataclass(frozen=True)
class CompiledVoiceFilterGraph:
    filters: tuple[str, ...]

    def filter_spec(self) -> str:
        return ",".join(self.filters)


@dataclass
class FfmpegFilterGraphCompiler:
    sample_rate_hz: int = 48000

    def compile(self, transforms: tuple[VoiceTransform, ...]) -> CompiledVoiceFilterGraph:
        filters: list[str] = []
        for transform in transforms:
            if transform.type == "pitch":
                filters.extend(self._pitch(transform))
            elif transform.type == "speed":
                filters.extend(self._speed(transform))
            elif transform.type == "highpass":
                filters.append(f"highpass=f={self._positive_float(transform, 'frequency_hz')}")
            elif transform.type == "lowpass":
                filters.append(f"lowpass=f={self._positive_float(transform, 'frequency_hz')}")
            elif transform.type == "eq":
                filters.append(self._eq(transform))
            elif transform.type == "filter_curve":
                filters.extend(self._filter_curve(transform))
            elif transform.type == "compressor":
                filters.append(self._compressor(transform))
            elif transform.type == "gain":
                filters.append(f"volume={self._float(transform, 'db')}dB")
            elif transform.type == "loudnorm":
                filters.append(self._loudnorm(transform))
            elif transform.type == "reverb":
                filters.append(self._reverb(transform))
            elif transform.type == "delay":
                filters.append(self._delay(transform))
            elif transform.type == "preset":
                raise RuntimeError("Preset transforms must be expanded before compiling an FFmpeg filter graph")
            else:
                raise RuntimeError(f"Unsupported voice transform type: {transform.type}")
        return CompiledVoiceFilterGraph(filters=tuple(filters))

    def _pitch(self, transform: VoiceTransform) -> list[str]:
        semitones = self._float(transform, "semitones")
        strategy = str(transform.params.get("strategy", PITCH_STRATEGY_AUTO))
        if strategy == PITCH_STRATEGY_AUTO:
            raise RuntimeError("Pitch strategy must be resolved before compiling an FFmpeg filter graph")
        factor = 2 ** (semitones / 12)
        filters = [
            f"asetrate={self.sample_rate_hz}*{self._fmt(factor)}",
            f"aresample={self.sample_rate_hz}",
        ]
        if strategy == PITCH_STRATEGY_PRESERVE_TEMPO:
            filters.extend(self._atempo_chain(1 / factor))
            return filters
        if strategy == PITCH_STRATEGY_LINKED_SPEED:
            return filters
        raise RuntimeError(f"Unsupported pitch strategy: {strategy}")

    def _speed(self, transform: VoiceTransform) -> list[str]:
        return self._atempo_chain(self._positive_float(transform, "speed_factor"))

    def _eq(self, transform: VoiceTransform) -> str:
        frequency = self._positive_float(transform, "frequency_hz")
        gain = self._float(transform, "gain_db")
        width = self._positive_float(transform, "width", default=1.0)
        width_type = str(transform.params.get("width_type", "o"))
        return f"equalizer=f={frequency}:width_type={width_type}:width={width}:g={gain}"

    def _filter_curve(self, transform: VoiceTransform) -> list[str]:
        points = transform.params.get("points")
        if not isinstance(points, list) or not points:
            raise RuntimeError("filter_curve transform requires non-empty points")
        filters = []
        for point in points:
            if not isinstance(point, list) or len(point) != 2:
                raise RuntimeError("filter_curve points must be [frequency_hz, gain_db] pairs")
            frequency = self._positive_number(point[0], "filter_curve frequency_hz")
            gain = self._number(point[1], "filter_curve gain_db")
            filters.append(f"equalizer=f={frequency}:width_type=o:width=1:g={gain}")
        return filters

    def _compressor(self, transform: VoiceTransform) -> str:
        threshold = self._float(transform, "threshold_db")
        ratio = self._positive_float(transform, "ratio")
        attack = self._positive_float(transform, "attack_ms", default=5.0)
        release = self._positive_float(transform, "release_ms", default=80.0)
        return f"acompressor=threshold={threshold}dB:ratio={ratio}:attack={attack}:release={release}"

    def _loudnorm(self, transform: VoiceTransform) -> str:
        integrated = self._float(transform, "integrated_lufs", default=-16.0)
        true_peak = self._float(transform, "true_peak_db", default=-1.5)
        lra = self._float(transform, "lra", default=11.0)
        return f"loudnorm=I={integrated}:TP={true_peak}:LRA={lra}"

    def _reverb(self, transform: VoiceTransform) -> str:
        in_gain = self._float(transform, "in_gain", default=0.8)
        out_gain = self._float(transform, "out_gain", default=0.9)
        delay_ms = self._positive_float(transform, "delay_ms", default=60.0)
        decay = self._positive_float(transform, "decay", default=0.35)
        return f"aecho={in_gain}:{out_gain}:{delay_ms}:{decay}"

    def _delay(self, transform: VoiceTransform) -> str:
        in_gain = self._float(transform, "in_gain", default=0.8)
        out_gain = self._float(transform, "out_gain", default=0.9)
        delay_ms = self._positive_float(transform, "delay_ms")
        decay = self._positive_float(transform, "decay", default=0.35)
        return f"aecho={in_gain}:{out_gain}:{delay_ms}:{decay}"

    def _atempo_chain(self, factor: float) -> list[str]:
        if factor <= 0:
            raise RuntimeError("atempo factor must be positive")
        filters = []
        remaining = factor
        while remaining > 2.0:
            filters.append("atempo=2")
            remaining /= 2.0
        while remaining < 0.5:
            filters.append("atempo=0.5")
            remaining /= 0.5
        filters.append(f"atempo={self._fmt(remaining)}")
        return filters

    def _positive_float(self, transform: VoiceTransform, name: str, default: float | None = None) -> float:
        value = self._float(transform, name, default=default)
        if value <= 0:
            raise RuntimeError(f"{transform.type} transform requires positive {name}")
        return value

    def _float(self, transform: VoiceTransform, name: str, default: float | None = None) -> float:
        if name not in transform.params:
            if default is None:
                raise RuntimeError(f"{transform.type} transform requires {name}")
            return default
        return self._number(transform.params[name], f"{transform.type} {name}")

    def _positive_number(self, value: object, name: str) -> float:
        parsed = self._number(value, name)
        if parsed <= 0:
            raise RuntimeError(f"{name} must be positive")
        return parsed

    def _number(self, value: object, name: str) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Invalid numeric value for {name}") from exc
        if not math.isfinite(parsed):
            raise RuntimeError(f"Invalid numeric value for {name}")
        return parsed

    def _fmt(self, value: float) -> str:
        return f"{value:.8f}".rstrip("0").rstrip(".")
