from __future__ import annotations

import json
from pathlib import Path

from stager.audio.audio_cleanup_review import AudioCleanupReviewWriter
from stager.shared import paths


def test_audio_cleanup_review_writer_summarizes_rendered_manifests(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    manifest_path = cfg.audio_out_dir / "cleaned" / "MEGAERA-gentle_voice_cleanup" / "batch_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(
            {
                "batch_id": "MEGAERA-gentle_voice_cleanup",
                "segments": [
                    {
                        "role": "MEGAERA",
                        "segment_id": "0_1_1",
                        "source_path": "build/test/audio/segments/MEGAERA/0_1_1.wav",
                    }
                ],
                "cleaned_boundaries": [
                    {
                        "role": "MEGAERA",
                        "segment_id": "0_1_1",
                        "original_start_sample": 0,
                        "original_end_sample": 100,
                        "original_center_sample": 50,
                        "cleaned_start_sample": 0,
                        "cleaned_end_sample": 90,
                        "warnings": ["end_shift"],
                        "output_path": "build/test/audio/cleaned/MEGAERA/0_1_1.wav",
                        "validation": {"fallback": True, "fallback_reason": "batch_duration_changed"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    analysis_dir = cfg.audio_out_dir / "cleanup_analysis"
    analysis_dir.mkdir(parents=True)
    (analysis_dir / "report.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "role": "MEGAERA",
                        "segment_id": "0_1_1",
                        "recommendation": {"id": "MEGAERA/0_1_1/cleanup-analysis-v1"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = AudioCleanupReviewWriter(paths_config=cfg).write((manifest_path,))

    data = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert result.entry_count == 1
    assert data["entries"][0]["batch_id"] == "MEGAERA-gentle_voice_cleanup"
    assert data["entries"][0]["analysis_recommendation_id"] == "MEGAERA/0_1_1/cleanup-analysis-v1"
    assert data["entries"][0]["duration_delta_samples"] == -10
    assert data["entries"][0]["fallback_reason"] == "batch_duration_changed"
    markdown = result.markdown_path.read_text(encoding="utf-8")
    assert "| MEGAERA-gentle_voice_cleanup | MEGAERA | 0_1_1 | MEGAERA/0_1_1/cleanup-analysis-v1 | -10 |" in markdown


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
