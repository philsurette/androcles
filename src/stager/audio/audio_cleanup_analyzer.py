from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
    floor_noise_id: str | None
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
            },
            "floor_noise_id": self.floor_noise_id,
            "recommendation": {
                "id": self.recommendation_id,
                "profile": self.recommended_profile,
                "confidence": self.confidence,
            },
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class AudioCleanupAnalysisReport:
    created_at: str
    play_id: str
    status: str
    entries: tuple[AudioCleanupAnalysisEntry, ...]

    def to_dict(self) -> dict:
        return {
            "created_at": self.created_at,
            "play_id": self.play_id,
            "status": self.status,
            "entries": [entry.to_dict() for entry in self.entries],
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
        warnings = self._warnings(channels=channels, peak=peak, rms=rms, clipped_ratio=clipped_ratio)
        recommended_profile = self._recommended_profile(warnings=warnings, rms=rms)
        confidence = "low"  # Until floor-noise-backed measurements are wired into the analyzer.
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
            floor_noise_id=self._floor_noise_id(role=role, segment_id=segment_id),
            recommendation_id=f"{role}/{segment_id}/cleanup-analysis-v1",
            recommended_profile=recommended_profile,
            confidence=confidence,
            warnings=tuple(warnings),
        )

    def _warnings(self, *, channels: int, peak: float, rms: float, clipped_ratio: float) -> list[str]:
        warnings = []
        if peak <= 0.0001:
            warnings.append("silent")
        elif rms < 0.01:
            warnings.append("too_quiet")
        if clipped_ratio >= 0.01:
            warnings.append("clipped")
        if channels > 1:
            warnings.append("unexpected_channels")
        return warnings

    def _recommended_profile(self, *, warnings: list[str], rms: float) -> str:
        if "silent" in warnings:
            return "none"
        if rms < 0.01:
            return "declick_gentle"
        return "gentle_voice_cleanup"

    def _floor_noise_id(self, *, role: str, segment_id: str) -> str | None:
        imports_dir = self.paths_config.build_dir / "linerecorder" / "imports"
        if not imports_dir.exists():
            return None
        for import_json in sorted(imports_dir.glob("*/import.json"), reverse=True):
            try:
                data = json.loads(import_json.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if data.get("role_id") != role:
                continue
            for imported in data.get("imported", []):
                if imported.get("segment_id") == segment_id:
                    floor_noise_id = imported.get("floor_noise_id")
                    return floor_noise_id if isinstance(floor_noise_id, str) else None
        return None

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
