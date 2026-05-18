from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from stager.shared import paths


@dataclass(frozen=True)
class AudioCleanupReviewResult:
    json_path: Path
    markdown_path: Path
    entry_count: int


@dataclass
class AudioCleanupReviewWriter:
    paths_config: paths.PathConfig

    def write(self, manifest_paths: tuple[Path, ...]) -> AudioCleanupReviewResult:
        entries = []
        for manifest_path in manifest_paths:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            batch_id = data["batch_id"]
            segments = {
                (segment["role"], segment["segment_id"]): segment
                for segment in data.get("segments", [])
                if isinstance(segment, dict)
            }
            for boundary in data.get("cleaned_boundaries", []):
                if not isinstance(boundary, dict):
                    continue
                segment = segments.get((boundary.get("role"), boundary.get("segment_id")), {})
                original_duration = boundary["original_end_sample"] - boundary["original_start_sample"]
                cleaned_duration = boundary["cleaned_end_sample"] - boundary["cleaned_start_sample"]
                validation = boundary.get("validation") if isinstance(boundary.get("validation"), dict) else {}
                entries.append(
                    {
                        "batch_id": batch_id,
                        "role": boundary["role"],
                        "segment_id": boundary["segment_id"],
                        "source_path": segment.get("source_path"),
                        "output_path": boundary.get("output_path"),
                        "original_start_sample": boundary["original_start_sample"],
                        "original_end_sample": boundary["original_end_sample"],
                        "cleaned_start_sample": boundary["cleaned_start_sample"],
                        "cleaned_end_sample": boundary["cleaned_end_sample"],
                        "duration_delta_samples": cleaned_duration - original_duration,
                        "warnings": list(boundary.get("warnings", [])),
                        "fallback": validation.get("fallback") is True,
                        "fallback_reason": validation.get("fallback_reason"),
                    }
                )
        output_dir = self.paths_config.audio_out_dir / "cleaned"
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "cleanup_review.json"
        markdown_path = output_dir / "cleanup_review.md"
        payload = {
            "play_id": self.paths_config.play_name,
            "entries": entries,
        }
        json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        markdown_path.write_text(self._markdown(entries), encoding="utf-8")
        return AudioCleanupReviewResult(
            json_path=json_path,
            markdown_path=markdown_path,
            entry_count=len(entries),
        )

    def _markdown(self, entries: list[dict]) -> str:
        lines = [
            "# Audio Cleanup Review",
            "",
            f"- Play: `{self.paths_config.play_name}`",
            f"- Segments: {len(entries)}",
            "",
            "| Batch | Role | Segment | Delta Samples | Warnings | Fallback | Output |",
            "| --- | --- | --- | ---: | --- | --- | --- |",
        ]
        for entry in entries:
            warnings = ", ".join(entry["warnings"]) if entry["warnings"] else "none"
            fallback = entry["fallback_reason"] if entry["fallback"] else "no"
            output_path = entry["output_path"] or ""
            lines.append(
                f"| {entry['batch_id']} | {entry['role']} | {entry['segment_id']} | "
                f"{entry['duration_delta_samples']} | {warnings} | {fallback} | {output_path} |"
            )
        return "\n".join(lines) + "\n"
