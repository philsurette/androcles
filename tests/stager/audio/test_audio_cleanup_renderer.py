from __future__ import annotations

import json
from pathlib import Path
import wave

from stager.audio.audio_cleanup_renderer import AudioCleanupRenderer
from stager.shared import paths


def test_cleanup_renderer_writes_batch_manifest_with_cleaned_ranges(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    first = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    second = cfg.segments_dir / "MEGAERA" / "0_1_2.wav"
    _write_wav(first, samples=[0, 1200, -1200, 0])
    _write_wav(second, samples=[0, 1500, -1500, 0])

    result = AudioCleanupRenderer(paths_config=cfg).prepare_batch(
        batch_id="MEGAERA-gentle_voice_cleanup",
        segment_paths=[first, second],
        padding_seconds=3.0,
        boundary_warning_ms=500,
        resolved_filters=("adeclick",),
    )

    data = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert data["batch_id"] == "MEGAERA-gentle_voice_cleanup"
    assert data["cache_key"]
    assert len(data["segments"]) == 2
    assert data["segments"][0]["source_hash"]
    assert len(data["cleaned_boundaries"]) == 2
    assert data["cleaned_boundaries"][0]["original_center_sample"] == 2


def test_cleanup_renderer_reports_cache_hit_on_second_prepare(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    first = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    _write_wav(first, samples=[0, 1200, -1200, 0])
    renderer = AudioCleanupRenderer(paths_config=cfg)

    first_result = renderer.prepare_batch(
        batch_id="MEGAERA-gentle_voice_cleanup",
        segment_paths=[first],
        padding_seconds=3.0,
        boundary_warning_ms=500,
        resolved_filters=("adeclick",),
    )
    second_result = renderer.prepare_batch(
        batch_id="MEGAERA-gentle_voice_cleanup",
        segment_paths=[first],
        padding_seconds=3.0,
        boundary_warning_ms=500,
        resolved_filters=("adeclick",),
    )

    assert first_result.cache_hit is False
    assert second_result.cache_hit is True


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


def _write_wav(path: Path, *, samples: list[int], sample_rate: int = 48_000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples))
