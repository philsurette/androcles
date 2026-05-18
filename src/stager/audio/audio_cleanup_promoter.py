from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from stager.shared import paths


@dataclass(frozen=True)
class AudioCleanupPromotionEntry:
    role: str
    segment_id: str
    batch_id: str
    cleaned_path: Path
    target_path: Path
    backup_path: Path | None
    warnings: tuple[str, ...]
    fallback: bool
    analysis_recommendation_id: str | None

    def to_dict(self) -> dict:
        data = {
            "role": self.role,
            "segment_id": self.segment_id,
            "batch_id": self.batch_id,
            "cleaned_path": paths.display_path(self.cleaned_path),
            "target_path": paths.display_path(self.target_path),
            "warnings": list(self.warnings),
            "fallback": self.fallback,
            "analysis_recommendation_id": self.analysis_recommendation_id,
        }
        if self.backup_path is not None:
            data["backup_path"] = paths.display_path(self.backup_path)
        return data


@dataclass(frozen=True)
class AudioCleanupPromotionResult:
    transaction_path: Path
    promoted_count: int
    skipped_count: int


@dataclass
class AudioCleanupPromoter:
    paths_config: paths.PathConfig

    def promote(
        self,
        *,
        confirm: bool,
        include_warnings: bool = False,
        role: str | None = None,
    ) -> AudioCleanupPromotionResult:
        if not confirm:
            raise RuntimeError("Audio cleanup promotion requires --confirm because it overwrites canonical segments.")
        review = self._load_review()
        transaction_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        transaction_dir = self.paths_config.audio_out_dir / "cleaned" / "promotions" / transaction_id
        promoted = []
        skipped_count = 0
        for review_entry in review.get("entries", []):
            if not isinstance(review_entry, dict):
                continue
            if role is not None and review_entry.get("role") != role:
                skipped_count += 1
                continue
            entry = self._promotion_entry(review_entry, transaction_dir)
            if (entry.warnings or entry.fallback) and not include_warnings:
                raise RuntimeError(
                    f"Refusing to promote {entry.role}/{entry.segment_id} because cleanup review contains "
                    "warnings or fallback output. Re-run with --include-warnings to promote reviewed output."
                )
            if not entry.cleaned_path.exists():
                raise RuntimeError(f"Cleaned audio does not exist: {paths.display_path(entry.cleaned_path)}")
            if entry.target_path.exists():
                if entry.backup_path is None:
                    raise RuntimeError(f"Missing backup path for {paths.display_path(entry.target_path)}")
                entry.backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(entry.target_path, entry.backup_path)
            entry.target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry.cleaned_path, entry.target_path)
            promoted.append(entry)
        if not promoted:
            raise RuntimeError("No audio cleanup review entries matched the promotion request.")
        transaction_path = transaction_dir / "promotion.json"
        transaction_path.parent.mkdir(parents=True, exist_ok=True)
        transaction_path.write_text(
            json.dumps(
                {
                    "id": transaction_id,
                    "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "play_id": self.paths_config.play_name,
                    "include_warnings": include_warnings,
                    "role": role,
                    "promoted": [entry.to_dict() for entry in promoted],
                    "skipped_count": skipped_count,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return AudioCleanupPromotionResult(
            transaction_path=transaction_path,
            promoted_count=len(promoted),
            skipped_count=skipped_count,
        )

    def _load_review(self) -> dict:
        review_path = self.paths_config.audio_out_dir / "cleaned" / "cleanup_review.json"
        if not review_path.exists():
            raise RuntimeError(
                "Audio cleanup promotion requires a cleanup review report. "
                "Run `./main audio-cleanup render` first."
            )
        return json.loads(review_path.read_text(encoding="utf-8"))

    def _promotion_entry(self, review_entry: dict, transaction_dir: Path) -> AudioCleanupPromotionEntry:
        role = review_entry.get("role")
        segment_id = review_entry.get("segment_id")
        batch_id = review_entry.get("batch_id")
        output_path = review_entry.get("output_path")
        if not isinstance(role, str) or not isinstance(segment_id, str) or not isinstance(batch_id, str):
            raise RuntimeError("Invalid audio cleanup review entry")
        if not isinstance(output_path, str) or not output_path:
            raise RuntimeError(f"Cleanup review entry has no output path for {role}/{segment_id}")
        target_path = self.paths_config.segments_dir / role / f"{segment_id}.wav"
        backup_path = transaction_dir / "backups" / role / f"{segment_id}.wav" if target_path.exists() else None
        fallback = review_entry.get("fallback") is True
        warnings = review_entry.get("warnings", [])
        recommendation_id = review_entry.get("analysis_recommendation_id")
        return AudioCleanupPromotionEntry(
            role=role,
            segment_id=segment_id,
            batch_id=batch_id,
            cleaned_path=self._path_from_review(output_path),
            target_path=target_path,
            backup_path=backup_path,
            warnings=tuple(warnings) if isinstance(warnings, list) else (),
            fallback=fallback,
            analysis_recommendation_id=recommendation_id if isinstance(recommendation_id, str) else None,
        )

    def _path_from_review(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return paths.project_root() / path
