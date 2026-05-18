from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
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


def test_cleanup_renderer_cache_key_includes_floor_noise(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    first = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    floor_noise = tmp_path / "floor.wav"
    _write_wav(first, samples=[0, 1200, -1200, 0])
    _write_wav(floor_noise, samples=[0, 1, -1, 0])
    renderer = AudioCleanupRenderer(paths_config=cfg)
    first_result = renderer.prepare_batch(
        batch_id="MEGAERA-gentle_voice_cleanup-floor-1",
        segment_paths=[first],
        padding_seconds=3.0,
        boundary_warning_ms=500,
        resolved_filters=("afftdn=nr=6:nf=-50",),
        floor_noise_path=floor_noise,
    )
    _write_wav(floor_noise, samples=[0, 2, -2, 0])

    second_result = renderer.prepare_batch(
        batch_id="MEGAERA-gentle_voice_cleanup-floor-1",
        segment_paths=[first],
        padding_seconds=3.0,
        boundary_warning_ms=500,
        resolved_filters=("afftdn=nr=6:nf=-50",),
        floor_noise_path=floor_noise,
    )

    assert first_result.manifest.cache_key != second_result.manifest.cache_key
    assert second_result.cache_hit is False


def test_cleanup_renderer_cache_key_includes_loudnorm_profile(tmp_path: Path) -> None:
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
        loudnorm_profile="none",
    )
    second_result = renderer.prepare_batch(
        batch_id="MEGAERA-gentle_voice_cleanup",
        segment_paths=[first],
        padding_seconds=3.0,
        boundary_warning_ms=500,
        resolved_filters=("adeclick",),
        loudnorm_profile="librivox",
    )

    assert first_result.manifest.cache_key != second_result.manifest.cache_key


def test_cleanup_renderer_runs_ffmpeg_and_writes_cleaned_segments(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    first = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    _write_wav(first, samples=[0, 1200, -1200, 0])
    runner = CopyingRunner()

    result = AudioCleanupRenderer(paths_config=cfg, command_runner=runner).render_batch(
        batch_id="MEGAERA-gentle_voice_cleanup",
        segment_paths=[first],
        padding_seconds=3.0,
        boundary_warning_ms=500,
        resolved_filters=("adeclick",),
    )

    output_path = cfg.audio_out_dir / "cleaned" / "MEGAERA-gentle_voice_cleanup" / "MEGAERA" / "0_1_1.wav"
    data = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert runner.commands[0][0] == "ffmpeg"
    assert output_path.exists()
    assert data["cleaned_boundaries"][0]["output_path"].endswith("MEGAERA/0_1_1.wav")
    assert data["cleaned_boundaries"][0]["validation"]["peak"] > 0
    assert result.rendered_count == 1


def test_cleanup_renderer_applies_loudnorm_after_splitting_segments(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    first = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    second = cfg.segments_dir / "MEGAERA" / "0_1_2.wav"
    _write_wav(first, samples=[0, 1200, -1200, 0])
    _write_wav(second, samples=[0, 1500, -1500, 0])
    runner = CopyingRunner()
    factory = RecordingNormalizerFactory()

    result = AudioCleanupRenderer(
        paths_config=cfg,
        command_runner=runner,
        normalizer_factory=factory,
    ).render_batch(
        batch_id="MEGAERA-gentle_voice_cleanup",
        segment_paths=[first, second],
        padding_seconds=3.0,
        boundary_warning_ms=500,
        resolved_filters=("adeclick",),
        loudnorm_profile="librivox",
    )

    assert result.rendered_count == 2
    assert factory.calls == [("librivox", 48_000), ("librivox", 48_000)]
    assert len(factory.normalizers[0].normalized) == 1
    assert len(factory.normalizers[1].normalized) == 1


def test_cleanup_renderer_rejects_duration_changing_filter_output(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    first = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    _write_wav(first, samples=[0, 1200, -1200, 0])

    renderer = AudioCleanupRenderer(paths_config=cfg, command_runner=ShorteningRunner())

    try:
        renderer.render_batch(
            batch_id="MEGAERA-gentle_voice_cleanup",
            segment_paths=[first],
            padding_seconds=3.0,
            boundary_warning_ms=500,
            resolved_filters=("adeclick",),
        )
    except RuntimeError as exc:
        assert "duration changed unexpectedly" in str(exc)
    else:
        raise AssertionError("Expected duration-changing output to fail")


def test_cleanup_renderer_uses_floor_noise_for_afftdn(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    first = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    floor_noise = tmp_path / "floor.wav"
    _write_wav(first, samples=[0, 1200, -1200, 0])
    _write_wav(floor_noise, samples=[0, 0, 10, -10])
    runner = CopyingRunner()

    AudioCleanupRenderer(paths_config=cfg, command_runner=runner).render_batch(
        batch_id="MEGAERA-gentle_voice_cleanup-floor-1",
        segment_paths=[first],
        padding_seconds=3.0,
        boundary_warning_ms=500,
        resolved_filters=("afftdn=nr=6:nf=-50",),
        floor_noise_path=floor_noise,
    )

    command = runner.commands[0]
    assert "-filter_complex" in command
    filter_spec = command[command.index("-filter_complex") + 1]
    assert "asendcmd=0.0 afftdn sn start" in filter_spec
    assert "afftdn=nr=6:nf=-50" in filter_spec
    assert "atrim=start=" in filter_spec


def test_cleanup_renderer_rejects_silent_cleaned_segment(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    first = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    _write_wav(first, samples=[0, 1200, -1200, 0])

    renderer = AudioCleanupRenderer(paths_config=cfg, command_runner=SilentRunner())

    try:
        renderer.render_batch(
            batch_id="MEGAERA-gentle_voice_cleanup",
            segment_paths=[first],
            padding_seconds=3.0,
            boundary_warning_ms=500,
            resolved_filters=("adeclick",),
        )
    except RuntimeError as exc:
        assert "output is silent" in str(exc)
    else:
        raise AssertionError("Expected silent output to fail")


def test_cleanup_renderer_rejects_clipped_cleaned_segment(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    first = cfg.segments_dir / "MEGAERA" / "0_1_1.wav"
    _write_wav(first, samples=[0, 1200, -1200, 0])

    renderer = AudioCleanupRenderer(paths_config=cfg, command_runner=ClippedRunner())

    try:
        renderer.render_batch(
            batch_id="MEGAERA-gentle_voice_cleanup",
            segment_paths=[first],
            padding_seconds=3.0,
            boundary_warning_ms=500,
            resolved_filters=("adeclick",),
        )
    except RuntimeError as exc:
        assert "output appears clipped" in str(exc)
    else:
        raise AssertionError("Expected clipped output to fail")


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


class CopyingRunner:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], *, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        input_index = command.index("-i") + 1
        if "-filter_complex" in command:
            input_index = command.index("-i", input_index + 1) + 1
        shutil.copy2(command[input_index], command[-1])
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")


class ShorteningRunner:
    def __call__(self, command: list[str], *, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        _write_wav(Path(command[-1]), samples=[0])
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")


class SilentRunner:
    def __call__(self, command: list[str], *, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        _write_wav(Path(command[-1]), samples=[0, 0, 0, 0])
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")


class ClippedRunner:
    def __call__(self, command: list[str], *, capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        _write_wav(Path(command[-1]), samples=[32767, 32767, 32767, 32767])
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")


class RecordingNormalizerFactory:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []
        self.normalizers: list[RecordingNormalizer] = []

    def __call__(self, profile_name: str, *, sample_rate_hz: int) -> "RecordingNormalizer":
        self.calls.append((profile_name, sample_rate_hz))
        normalizer = RecordingNormalizer()
        self.normalizers.append(normalizer)
        return normalizer


class RecordingNormalizer:
    def __init__(self) -> None:
        self.normalized: list[tuple[str, str]] = []

    def normalize(self, input_file: str, output_file: str | None = None):
        if output_file is None:
            raise RuntimeError("Expected explicit loudnorm output path")
        self.normalized.append((input_file, output_file))
        shutil.copy2(input_file, output_file)
