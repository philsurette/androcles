from __future__ import annotations

import json
from pathlib import Path

import pytest

from stager.audio.audio_cleanup_promoter import AudioCleanupPromoter
from stager.shared import paths


def test_audio_cleanup_promoter_requires_confirmation(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    _write_review(cfg)

    with pytest.raises(RuntimeError, match="requires --confirm"):
        AudioCleanupPromoter(paths_config=cfg).promote(confirm=False)


def test_audio_cleanup_promoter_copies_cleaned_audio_and_writes_transaction(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    target_path = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    cleaned_path = cfg.audio_out_dir / "cleaned" / "MEGAERA-none" / "MEGAERA" / "0_1_1.wav"
    target_path.parent.mkdir(parents=True)
    target_path.write_bytes(b"canonical")
    cleaned_path.parent.mkdir(parents=True)
    cleaned_path.write_bytes(b"cleaned")
    _write_review(cfg, output_path=cleaned_path)

    result = AudioCleanupPromoter(paths_config=cfg).promote(confirm=True)

    assert result.promoted_count == 1
    assert target_path.read_bytes() == b"cleaned"
    transaction = json.loads(result.transaction_path.read_text(encoding="utf-8"))
    backup_path = Path(transaction["promoted"][0]["backup_path"])
    assert backup_path.read_bytes() == b"canonical"
    assert transaction["promoted"][0]["analysis_recommendation_id"] == "MEGAERA/0_1_1/cleanup-analysis-v1"


def test_audio_cleanup_promoter_blocks_warnings_by_default(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    cleaned_path = cfg.audio_out_dir / "cleaned" / "MEGAERA-none" / "MEGAERA" / "0_1_1.wav"
    cleaned_path.parent.mkdir(parents=True)
    cleaned_path.write_bytes(b"cleaned")
    _write_review(cfg, output_path=cleaned_path, warnings=["end_moved"])

    with pytest.raises(RuntimeError, match="warnings or fallback"):
        AudioCleanupPromoter(paths_config=cfg).promote(confirm=True)

    result = AudioCleanupPromoter(paths_config=cfg).promote(confirm=True, include_warnings=True)

    assert result.promoted_count == 1


def _config(tmp_path: Path) -> paths.PathConfig:
    cfg = paths.PathConfig(
        play_name="test",
        root=tmp_path / "src",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )
    cfg.play_dir.mkdir(parents=True, exist_ok=True)
    return cfg


def _write_review(
    cfg: paths.PathConfig,
    *,
    output_path: Path | None = None,
    warnings: list[str] | None = None,
) -> None:
    path = cfg.audio_out_dir / "cleaned" / "cleanup_review.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "play_id": cfg.play_name,
                "entries": [
                    {
                        "batch_id": "MEGAERA-none",
                        "role": "MEGAERA",
                        "segment_id": "0_1_1",
                        "analysis_recommendation_id": "MEGAERA/0_1_1/cleanup-analysis-v1",
                        "output_path": (output_path or Path("/tmp/cleaned.wav")).as_posix(),
                        "warnings": warnings or [],
                        "fallback": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
