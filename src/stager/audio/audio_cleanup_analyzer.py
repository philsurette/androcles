from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import json
from pathlib import Path
import wave

from stager.shared import paths


@dataclass(frozen=True)
class AudioCleanupAnalysisEntry:
    role: str
    segment_id: str
    source_path: Path
    duration_ms: int
    sample_rate_hz: int
    channels: int
    peak: float
    rms: float
    clipped_ratio: float
    import_session_id: str | None
    floor_noise_id: str | None
    floor_noise_path: Path | None
    noise_source: str
    noise_floor_rms: float | None
    noise_floor_dbfs: float | None
    suggested_denoise: str
    click_density: float
    sibilance_risk: str
    suggested_deesser: str
    leading_trim_ms: int
    trailing_trim_ms: int
    rough_loudness_dbfs: float | None
    expected_loudnorm_gain_db: float | None
    recommendation_id: str
    recommended_profile: str
    confidence: str
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "segment_id": self.segment_id,
            "source_path": paths.display_path(self.source_path),
            "duration_ms": self.duration_ms,
            "sample_rate_hz": self.sample_rate_hz,
            "channels": self.channels,
            "measurements": {
                "peak": round(self.peak, 6),
                "rms": round(self.rms, 6),
                "clipped_ratio": round(self.clipped_ratio, 6),
                "noise_source": self.noise_source,
                "noise_floor_rms": self._rounded(self.noise_floor_rms),
                "noise_floor_dbfs": self._rounded(self.noise_floor_dbfs),
                "suggested_denoise": self.suggested_denoise,
                "click_density": round(self.click_density, 6),
                "sibilance_risk": self.sibilance_risk,
                "suggested_deesser": self.suggested_deesser,
                "leading_trim_ms": self.leading_trim_ms,
                "trailing_trim_ms": self.trailing_trim_ms,
                "rough_loudness_dbfs": self._rounded(self.rough_loudness_dbfs),
                "expected_loudnorm_gain_db": self._rounded(self.expected_loudnorm_gain_db),
            },
            "import_session_id": self.import_session_id,
            "floor_noise_id": self.floor_noise_id,
            "floor_noise_path": paths.display_path(self.floor_noise_path) if self.floor_noise_path else None,
            "recommendation": {
                "id": self.recommendation_id,
                "profile": self.recommended_profile,
                "confidence": self.confidence,
            },
            "warnings": list(self.warnings),
        }

    def _rounded(self, value: float | None) -> float | None:
        return round(value, 6) if value is not None else None


@dataclass(frozen=True)
class AudioCleanupAnalysisGroup:
    id: str
    role: str
    import_session_id: str | None
    floor_noise_id: str | None
    sample_rate_hz: int
    channels: int
    noise_source: str
    suggested_denoise: str
    sibilance_risk: str
    recommended_profile: str
    segment_ids: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "import_session_id": self.import_session_id,
            "floor_noise_id": self.floor_noise_id,
            "source_characteristics": {
                "sample_rate_hz": self.sample_rate_hz,
                "channels": self.channels,
                "noise_source": self.noise_source,
                "suggested_denoise": self.suggested_denoise,
                "sibilance_risk": self.sibilance_risk,
            },
            "recommendation": {
                "profile": self.recommended_profile,
            },
            "segment_ids": list(self.segment_ids),
        }


@dataclass(frozen=True)
class AudioCleanupAnalysisReport:
    created_at: str
    play_id: str
    status: str
    entries: tuple[AudioCleanupAnalysisEntry, ...]
    groups: tuple[AudioCleanupAnalysisGroup, ...]

    def to_dict(self) -> dict:
        return {
            "created_at": self.created_at,
            "play_id": self.play_id,
            "status": self.status,
            "entries": [entry.to_dict() for entry in self.entries],
            "groups": [group.to_dict() for group in self.groups],
        }


@dataclass
class AudioCleanupAnalyzer:
    paths_config: paths.PathConfig

    def analyze(self, *, role: str | None = None) -> AudioCleanupAnalysisReport:
        entries = []
        for audio_path in self._segment_paths(role=role):
            entries.append(self._analyze_segment(audio_path))
        return AudioCleanupAnalysisReport(
            created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            play_id=self.paths_config.play_name,
            status="accepted",
            entries=tuple(entries),
            groups=self._groups(entries),
        )

    def write_report(self, report: AudioCleanupAnalysisReport) -> tuple[Path, Path]:
        report_dir = self.paths_config.audio_out_dir / "cleanup_analysis"
        report_dir.mkdir(parents=True, exist_ok=True)
        json_path = report_dir / "report.json"
        markdown_path = report_dir / "report.md"
        json_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
        markdown_path.write_text(self._render_markdown(report), encoding="utf-8")
        return json_path, markdown_path

    def _segment_paths(self, *, role: str | None) -> list[Path]:
        segments_dir = self.paths_config.segments_dir
        if not segments_dir.exists():
            return []
        if role is not None:
            role_dir = segments_dir / role
            return sorted(role_dir.glob("*.wav")) if role_dir.exists() else []
        return sorted(path for role_dir in segments_dir.iterdir() if role_dir.is_dir() for path in role_dir.glob("*.wav"))

    def _analyze_segment(self, audio_path: Path) -> AudioCleanupAnalysisEntry:
        role = audio_path.parent.name
        segment_id = audio_path.stem
        with wave.open(str(audio_path), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frame_count = wav.getnframes()
            frames = wav.readframes(frame_count)
        samples = self._normalized_samples(frames, sample_width)
        duration_ms = round(frame_count / sample_rate * 1000) if sample_rate else 0
        peak = max((abs(sample) for sample in samples), default=0)
        rms = (sum(sample * sample for sample in samples) / len(samples)) ** 0.5 if samples else 0
        clipped_ratio = (
            sum(1 for sample in samples if abs(sample) >= 0.999) / len(samples)
            if samples
            else 0
        )
        import_session_id, floor_noise_id, floor_noise_path = self._floor_noise_context(
            role=role,
            segment_id=segment_id,
        )
        noise_source, noise_floor_rms = self._noise_floor(samples, sample_rate, floor_noise_path)
        noise_floor_dbfs = self._dbfs(noise_floor_rms)
        suggested_denoise = self._suggested_denoise(noise_floor_dbfs)
        click_density = self._click_density(samples)
        sibilance_risk = self._sibilance_risk(samples)
        suggested_deesser = "gentle" if sibilance_risk in {"medium", "high"} else "none"
        leading_trim_ms, trailing_trim_ms = self._trim_candidates(samples, sample_rate, noise_floor_rms)
        rough_loudness_dbfs = self._dbfs(rms)
        expected_loudnorm_gain_db = (
            round(-20.0 - rough_loudness_dbfs, 3) if rough_loudness_dbfs is not None else None
        )
        warnings = self._warnings(
            channels=channels,
            peak=peak,
            rms=rms,
            clipped_ratio=clipped_ratio,
            noise_source=noise_source,
            click_density=click_density,
            sibilance_risk=sibilance_risk,
            expected_loudnorm_gain_db=expected_loudnorm_gain_db,
        )
        recommended_profile = self._recommended_profile(
            warnings=warnings,
            rms=rms,
            suggested_denoise=suggested_denoise,
            click_density=click_density,
            suggested_deesser=suggested_deesser,
        )
        confidence = "medium" if noise_source == "floor_noise" else "low"
        return AudioCleanupAnalysisEntry(
            role=role,
            segment_id=segment_id,
            source_path=audio_path,
            duration_ms=duration_ms,
            sample_rate_hz=sample_rate,
            channels=channels,
            peak=peak,
            rms=rms,
            clipped_ratio=clipped_ratio,
            import_session_id=import_session_id,
            floor_noise_id=floor_noise_id,
            floor_noise_path=floor_noise_path,
            noise_source=noise_source,
            noise_floor_rms=noise_floor_rms,
            noise_floor_dbfs=noise_floor_dbfs,
            suggested_denoise=suggested_denoise,
            click_density=click_density,
            sibilance_risk=sibilance_risk,
            suggested_deesser=suggested_deesser,
            leading_trim_ms=leading_trim_ms,
            trailing_trim_ms=trailing_trim_ms,
            rough_loudness_dbfs=rough_loudness_dbfs,
            expected_loudnorm_gain_db=expected_loudnorm_gain_db,
            recommendation_id=f"{role}/{segment_id}/cleanup-analysis-v1",
            recommended_profile=recommended_profile,
            confidence=confidence,
            warnings=tuple(warnings),
        )

    def _warnings(
        self,
        *,
        channels: int,
        peak: float,
        rms: float,
        clipped_ratio: float,
        noise_source: str,
        click_density: float,
        sibilance_risk: str,
        expected_loudnorm_gain_db: float | None,
    ) -> list[str]:
        warnings = []
        if peak <= 0.0001:
            warnings.append("silent")
        elif rms < 0.01:
            warnings.append("too_quiet")
        if clipped_ratio >= 0.01:
            warnings.append("clipped")
        if channels > 1:
            warnings.append("unexpected_channels")
        if noise_source == "quiet_region":
            warnings.append("noise_floor_estimated_from_quiet_regions")
        elif noise_source == "unavailable":
            warnings.append("noise_floor_unavailable")
        if click_density >= 0.02:
            warnings.append("click_heavy")
        if sibilance_risk == "high":
            warnings.append("sibilance_risk_high")
        if expected_loudnorm_gain_db is not None and abs(expected_loudnorm_gain_db) >= 18:
            warnings.append("large_loudnorm_gain")
        return warnings

    def _recommended_profile(
        self,
        *,
        warnings: list[str],
        rms: float,
        suggested_denoise: str,
        click_density: float,
        suggested_deesser: str,
    ) -> str:
        if "silent" in warnings:
            return "none"
        if rms < 0.01:
            return "declick_gentle"
        if click_density >= 0.005:
            return "declick_gentle"
        if suggested_deesser != "none":
            return "deesser_gentle"
        if suggested_denoise != "none":
            return "denoise_light"
        return "gentle_voice_cleanup"

    def _groups(self, entries: list[AudioCleanupAnalysisEntry]) -> tuple[AudioCleanupAnalysisGroup, ...]:
        grouped: dict[tuple, list[AudioCleanupAnalysisEntry]] = {}
        for entry in entries:
            key = (
                entry.role,
                entry.import_session_id,
                entry.floor_noise_id,
                entry.sample_rate_hz,
                entry.channels,
                entry.noise_source,
                entry.suggested_denoise,
                entry.sibilance_risk,
                entry.recommended_profile,
            )
            grouped.setdefault(key, []).append(entry)
        groups = []
        for index, (key, grouped_entries) in enumerate(
            sorted(
                grouped.items(),
                key=lambda item: tuple("" if value is None else value for value in item[0]),
            ),
            start=1,
        ):
            (
                role,
                import_session_id,
                floor_noise_id,
                sample_rate_hz,
                channels,
                noise_source,
                suggested_denoise,
                sibilance_risk,
                recommended_profile,
            ) = key
            groups.append(
                AudioCleanupAnalysisGroup(
                    id=f"cleanup-analysis-group-{index}",
                    role=role,
                    import_session_id=import_session_id,
                    floor_noise_id=floor_noise_id,
                    sample_rate_hz=sample_rate_hz,
                    channels=channels,
                    noise_source=noise_source,
                    suggested_denoise=suggested_denoise,
                    sibilance_risk=sibilance_risk,
                    recommended_profile=recommended_profile,
                    segment_ids=tuple(
                        entry.segment_id for entry in sorted(grouped_entries, key=lambda item: item.segment_id)
                    ),
                )
            )
        return tuple(groups)

    def _floor_noise_context(self, *, role: str, segment_id: str) -> tuple[str | None, str | None, Path | None]:
        imports_dir = self.paths_config.build_dir / "linerecorder" / "imports"
        if not imports_dir.exists():
            return None, None, None
        for import_json in sorted(imports_dir.glob("*/import.json"), reverse=True):
            try:
                data = json.loads(import_json.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if data.get("role_id") != role:
                continue
            floor_noise_paths = self._floor_noise_paths(data, import_json.parent)
            for imported in data.get("imported", []):
                if imported.get("segment_id") == segment_id:
                    floor_noise_id = imported.get("floor_noise_id")
                    if not isinstance(floor_noise_id, str):
                        return import_json.parent.name, None, None
                    return import_json.parent.name, floor_noise_id, floor_noise_paths.get(floor_noise_id)
        return None, None, None

    def _floor_noise_paths(self, transaction: dict, transaction_dir: Path) -> dict[str, Path]:
        floor_noise_paths = {}
        for floor_noise in transaction.get("floor_noise_recordings", []) or []:
            if not isinstance(floor_noise, dict):
                continue
            floor_noise_id = floor_noise.get("id")
            if not isinstance(floor_noise_id, str):
                continue
            artifact_path = floor_noise.get("artifact_path")
            path = Path(artifact_path) if isinstance(artifact_path, str) else None
            if path is not None and not path.is_absolute():
                path = paths.project_root() / path
            if path is None or not path.exists():
                path = self._floor_noise_path(transaction_dir, floor_noise_id)
            if path is not None and path.exists():
                floor_noise_paths[floor_noise_id] = path
        return floor_noise_paths

    def _floor_noise_path(self, transaction_dir: Path, floor_noise_id: str) -> Path | None:
        floor_noise_dir = transaction_dir / "floor_noise"
        if not floor_noise_dir.exists():
            return None
        candidates = sorted(floor_noise_dir.rglob(f"{floor_noise_id}.wav"))
        return candidates[-1] if candidates else None

    def _noise_floor(self, samples: list[float], sample_rate: int, floor_noise_path: Path | None) -> tuple[str, float | None]:
        if floor_noise_path is not None and floor_noise_path.exists():
            floor_noise_samples = self._samples_from_wav(floor_noise_path)
            floor_noise_rms = self._rms(floor_noise_samples)
            if floor_noise_rms is not None:
                return "floor_noise", floor_noise_rms
        quiet_region = self._quiet_region_samples(samples, sample_rate)
        quiet_region_rms = self._rms(quiet_region)
        if quiet_region_rms is not None:
            return "quiet_region", quiet_region_rms
        return "unavailable", None

    def _samples_from_wav(self, path: Path) -> list[float]:
        with wave.open(str(path), "rb") as wav:
            sample_width = wav.getsampwidth()
            frames = wav.readframes(wav.getnframes())
        return self._normalized_samples(frames, sample_width)

    def _quiet_region_samples(self, samples: list[float], sample_rate: int) -> list[float]:
        if not samples or sample_rate <= 0:
            return []
        window_size = min(max(sample_rate // 4, 1), max(len(samples) // 5, 1))
        if len(samples) <= window_size:
            return []
        leading = samples[:window_size]
        trailing = samples[-window_size:]
        return leading if (self._rms(leading) or 0) <= (self._rms(trailing) or 0) else trailing

    def _suggested_denoise(self, noise_floor_dbfs: float | None) -> str:
        if noise_floor_dbfs is None:
            return "none"
        if noise_floor_dbfs >= -45:
            return "light"
        return "none"

    def _click_density(self, samples: list[float]) -> float:
        if len(samples) < 3:
            return 0
        click_count = 0
        for previous, current, next_sample in zip(samples, samples[1:], samples[2:]):
            if abs(current - previous) >= 0.35 and abs(current - next_sample) >= 0.35:
                click_count += 1
        return click_count / len(samples)

    def _sibilance_risk(self, samples: list[float]) -> str:
        active_samples = [sample for sample in samples if abs(sample) >= 0.01]
        if len(active_samples) < 20:
            return "low"
        zero_crossings = sum(
            1
            for previous, current in zip(active_samples, active_samples[1:])
            if (previous < 0 <= current) or (previous >= 0 > current)
        )
        ratio = zero_crossings / len(active_samples)
        if ratio >= 0.45:
            return "high"
        if ratio >= 0.25:
            return "medium"
        return "low"

    def _trim_candidates(self, samples: list[float], sample_rate: int, noise_floor_rms: float | None) -> tuple[int, int]:
        if not samples or sample_rate <= 0:
            return 0, 0
        threshold = max((noise_floor_rms or 0) * 3, 0.005)
        first = next((index for index, sample in enumerate(samples) if abs(sample) >= threshold), None)
        last = next((len(samples) - index - 1 for index, sample in enumerate(reversed(samples)) if abs(sample) >= threshold), None)
        if first is None or last is None or first > last:
            return 0, 0
        leading_ms = round(first / sample_rate * 1000)
        trailing_ms = round((len(samples) - last - 1) / sample_rate * 1000)
        return leading_ms, trailing_ms

    def _rms(self, samples: list[float]) -> float | None:
        if not samples:
            return None
        return (sum(sample * sample for sample in samples) / len(samples)) ** 0.5

    def _dbfs(self, rms: float | None) -> float | None:
        if rms is None or rms <= 0:
            return None
        return 20 * math.log10(rms)

    def _normalized_samples(self, frames: bytes, sample_width: int) -> list[float]:
        samples = []
        for offset in range(0, len(frames), sample_width):
            sample_bytes = frames[offset : offset + sample_width]
            if len(sample_bytes) != sample_width:
                break
            if sample_width == 1:
                sample = (sample_bytes[0] - 128) / 128
            elif sample_width == 2:
                sample = int.from_bytes(sample_bytes, "little", signed=True) / 32768
            elif sample_width == 3:
                sample = int.from_bytes(
                    sample_bytes + (b"\xff" if sample_bytes[-1] & 0x80 else b"\x00"),
                    "little",
                    signed=True,
                ) / 8388608
            elif sample_width == 4:
                sample = int.from_bytes(sample_bytes, "little", signed=True) / 2147483648
            else:
                return []
            samples.append(sample)
        return samples

    def _render_markdown(self, report: AudioCleanupAnalysisReport) -> str:
        lines = [
            "# Audio Cleanup Analysis",
            "",
            f"- Play: `{report.play_id}`",
            f"- Created: `{report.created_at}`",
            f"- Status: `{report.status}`",
            f"- Segments: {len(report.entries)}",
            f"- Groups: {len(report.groups)}",
            "",
            "| Role | Segment | Recommendation | Confidence | Warnings |",
            "| --- | --- | --- | --- | --- |",
        ]
        for entry in report.entries:
            warnings = ", ".join(entry.warnings) if entry.warnings else "none"
            lines.append(
                f"| {entry.role} | {entry.segment_id} | {entry.recommended_profile} | "
                f"{entry.confidence} | {warnings} |"
            )
        return "\n".join(lines) + "\n"


class AudioCleanupAnalysisStore:
    def __init__(self, paths_config: paths.PathConfig) -> None:
        self.paths_config = paths_config

    @property
    def report_path(self) -> Path:
        return self.paths_config.audio_out_dir / "cleanup_analysis" / "report.json"

    def load(self) -> dict:
        if not self.report_path.exists():
            raise RuntimeError(
                "Analysis-based audio cleanup requires an accepted analysis report. "
                "Run `./main audio-cleanup analyze` first."
            )
        return json.loads(self.report_path.read_text(encoding="utf-8"))

    def require_role(self, role: str) -> None:
        self.recommendations_for_role(role)

    def recommendations_for_role(self, role: str) -> tuple[dict, ...]:
        report = self.load()
        if report.get("status") != "accepted":
            raise RuntimeError(f"Audio cleanup analysis report is not accepted: {paths.display_path(self.report_path)}")
        entries = report.get("entries", [])
        role_entries = tuple(entry for entry in entries if isinstance(entry, dict) and entry.get("role") == role)
        if not role_entries:
            raise RuntimeError(
                f"Analysis-based audio cleanup has no recommendation for role {role}: "
                f"{paths.display_path(self.report_path)}"
            )
        return role_entries
