from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

from stager.shared import paths


AUDIO_SOURCE_AUTO = "auto"
AUDIO_SOURCE_CANONICAL = "canonical"
AUDIO_SOURCE_CLEANED = "cleaned"
SUPPORTED_AUDIO_SOURCES = {AUDIO_SOURCE_AUTO, AUDIO_SOURCE_CANONICAL, AUDIO_SOURCE_CLEANED}


@dataclass
class CleanedAudioSelector:
    paths_config: paths.PathConfig
    audio_source: str = AUDIO_SOURCE_AUTO
    _index: dict[tuple[str, str], Path] | None = field(default=None, init=False, repr=False)

    def segment_path(self, role: str, segment_id: str) -> Path:
        if self.audio_source not in SUPPORTED_AUDIO_SOURCES:
            raise RuntimeError(f"Invalid audio source {self.audio_source!r}")
        canonical_path = self.paths_config.segments_dir / role / f"{segment_id}.wav"
        if self.audio_source == AUDIO_SOURCE_CANONICAL:
            return canonical_path
        review_path = self._review_path()
        if self.audio_source == AUDIO_SOURCE_AUTO and not review_path.exists():
            return canonical_path
        index = self._review_index()
        cleaned_path = index.get((role, segment_id))
        if cleaned_path is None:
            raise RuntimeError(
                f"{self._request_description()} but no cleanup review output exists for "
                f"{role}/{segment_id}. Run `./main audio-cleanup render` first."
            )
        if not cleaned_path.exists():
            raise RuntimeError(f"Cleaned audio file missing: {paths.display_path(cleaned_path)}")
        return cleaned_path

    def _review_index(self) -> dict[tuple[str, str], Path]:
        if self._index is not None:
            return self._index
        review_path = self._review_path()
        if not review_path.exists():
            raise RuntimeError(
                "Cleaned audio was requested, but cleanup_review.json does not exist. "
                "Run `./main audio-cleanup render` first."
            )
        review = json.loads(review_path.read_text(encoding="utf-8"))
        index = {}
        for entry in review.get("entries", []):
            if not isinstance(entry, dict):
                continue
            role = entry.get("role")
            segment_id = entry.get("segment_id")
            output_path = entry.get("output_path")
            if not isinstance(role, str) or not isinstance(segment_id, str) or not isinstance(output_path, str):
                continue
            index[(role, segment_id)] = self._path_from_review(output_path)
        self._index = index
        return index

    def _review_path(self) -> Path:
        return self.paths_config.audio_out_dir / "cleaned" / "cleanup_review.json"

    def _request_description(self) -> str:
        if self.audio_source == AUDIO_SOURCE_CLEANED:
            return "Cleaned audio was requested,"
        return "A cleanup review exists, so cleaned audio was selected,"

    def _path_from_review(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return paths.project_root() / path
