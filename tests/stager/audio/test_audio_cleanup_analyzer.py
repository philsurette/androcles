from __future__ import annotations

import json
from pathlib import Path
import wave

from stager.audio.audio_cleanup_analyzer import AudioCleanupAnalysisStore, AudioCleanupAnalyzer
from stager.shared import paths


def test_audio_cleanup_analyzer_writes_reports(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", samples=[0, 1200, -1200, 0])

    result = AudioCleanupAnalyzer(paths_config=cfg).analyze()
    json_path, markdown_path = AudioCleanupAnalyzer(paths_config=cfg).write_report(result)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["status"] == "accepted"
    assert data["entries"][0]["role"] == "MEGAERA"
    assert data["entries"][0]["segment_id"] == "0_1_1"
    assert data["entries"][0]["recommendation"]["profile"] == "gentle_voice_cleanup"
    assert markdown_path.read_text(encoding="utf-8").startswith("# Audio Cleanup Analysis")


def test_audio_cleanup_analyzer_records_floor_noise_id_from_latest_import(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", samples=[0, 1200, -1200, 0])
    import_dir = cfg.build_dir / "linerecorder" / "imports" / "20260518T010101Z"
    import_dir.mkdir(parents=True)
    (import_dir / "import.json").write_text(
        json.dumps(
            {
                "role_id": "MEGAERA",
                "imported": [
                    {
                        "segment_id": "0_1_1",
                        "floor_noise_id": "floor-1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = AudioCleanupAnalyzer(paths_config=cfg).analyze()

    assert result.entries[0].floor_noise_id == "floor-1"


def test_audio_cleanup_analyzer_uses_floor_noise_signal_analysis(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    _write_wav(
        cfg.segments_dir / "MEGAERA" / "0_1_1.wav",
        samples=[8000, 7000, 8000, 7000] * 40,
    )
    import_dir = cfg.build_dir / "linerecorder" / "imports" / "20260518T010101Z"
    floor_noise_path = import_dir / "floor_noise" / "noise" / "floor-1.wav"
    _write_wav(floor_noise_path, samples=[1200, -1200] * 50)
    import_dir.mkdir(parents=True, exist_ok=True)
    (import_dir / "import.json").write_text(
        json.dumps(
            {
                "role_id": "MEGAERA",
                "floor_noise_recordings": [
                    {
                        "id": "floor-1",
                        "audio_path": "noise/floor-1.wav",
                        "artifact_path": floor_noise_path.as_posix(),
                        "recorded_at": "2026-05-18T01:00:00Z",
                        "duration_ms": 100,
                    }
                ],
                "imported": [
                    {
                        "segment_id": "0_1_1",
                        "floor_noise_id": "floor-1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = AudioCleanupAnalyzer(paths_config=cfg).analyze()
    entry = result.entries[0]

    assert entry.floor_noise_id == "floor-1"
    assert entry.floor_noise_path == floor_noise_path
    assert entry.noise_source == "floor_noise"
    assert entry.confidence == "medium"
    assert entry.suggested_denoise == "light"
    assert entry.recommended_profile in {"denoise_light", "gentle_voice_cleanup"}
    assert result.groups[0].role == "MEGAERA"
    assert result.groups[0].import_session_id == "20260518T010101Z"
    assert result.groups[0].floor_noise_id == "floor-1"
    assert result.groups[0].segment_ids == ("0_1_1",)


def test_audio_cleanup_analyzer_falls_back_to_quiet_region_analysis(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    samples = [100] * 250 + [0, 6000, -6000, 0] * 100 + [90] * 250
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", samples=samples, sample_rate=1000)

    result = AudioCleanupAnalyzer(paths_config=cfg).analyze()
    entry = result.entries[0]

    assert entry.noise_source == "quiet_region"
    assert entry.confidence == "low"
    assert "noise_floor_estimated_from_quiet_regions" in entry.warnings
    assert entry.leading_trim_ms > 0
    assert entry.trailing_trim_ms > 0


def test_audio_cleanup_analyzer_keeps_aggressive_click_recommendations_opt_in(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    samples = [0, 20000, 0, -20000] * 50
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", samples=samples)

    result = AudioCleanupAnalyzer(paths_config=cfg).analyze()
    entry = result.entries[0]

    assert entry.click_density >= 0.02
    assert "click_heavy" in entry.warnings
    assert entry.recommended_profile == "declick_gentle"


def test_analysis_store_requires_existing_role_recommendation(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", samples=[0, 1200, -1200, 0])
    analyzer = AudioCleanupAnalyzer(paths_config=cfg)
    analyzer.write_report(analyzer.analyze())

    AudioCleanupAnalysisStore(cfg).require_role("MEGAERA")


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
