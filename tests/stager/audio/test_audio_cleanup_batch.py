from __future__ import annotations

from pathlib import Path
import wave

import pytest

from stager.audio.audio_cleanup_batch import AudioCleanupBatchBuilder


def test_cleanup_batch_builder_records_sample_accurate_anchors(tmp_path: Path) -> None:
    first = tmp_path / "segments" / "MEGAERA" / "0_1_1.wav"
    second = tmp_path / "segments" / "MEGAERA" / "0_1_2.wav"
    _write_wav(first, samples=[0] * 100, sample_rate=1000)
    _write_wav(second, samples=[0] * 50, sample_rate=1000)

    manifest = AudioCleanupBatchBuilder(sample_rate_hz=1000).build(
        batch_id="batch-1",
        segment_paths=[first, second],
        padding_seconds=3.0,
    )

    assert manifest.padding_samples == 3000
    assert manifest.total_samples == 3150
    assert manifest.segments[0].batch_start_sample == 0
    assert manifest.segments[0].batch_end_sample == 100
    assert manifest.segments[0].center_sample == 50
    assert manifest.segments[0].guard_after_samples == 3000
    assert manifest.segments[1].guard_before_samples == 3000
    assert manifest.segments[1].batch_start_sample == 3100
    assert manifest.segments[1].batch_end_sample == 3150
    assert manifest.segments[1].center_sample == 3125


def test_cleanup_batch_builder_rejects_sample_rate_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "segments" / "MEGAERA" / "0_1_1.wav"
    _write_wav(path, samples=[0] * 100, sample_rate=44_100)

    with pytest.raises(RuntimeError, match="expected 48000 Hz"):
        AudioCleanupBatchBuilder(sample_rate_hz=48_000).build(
            batch_id="batch-1",
            segment_paths=[path],
            padding_seconds=3.0,
        )


def _write_wav(path: Path, *, samples: list[int], sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples))
