from __future__ import annotations

import json
from pathlib import Path
import wave

from stager.audio.audio_cleanup_service import AudioCleanupService
from stager.shared import paths
from stager.shared.ffmpeg_probe import FfmpegInstallation


def test_audio_cleanup_service_groups_segments_by_floor_noise(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", samples=[0, 1200, -1200, 0])
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_2.wav", samples=[0, 1300, -1300, 0])
    import_dir = cfg.build_dir / "linerecorder" / "imports" / "20260518T010101Z"
    floor_noise_path = import_dir / "floor_noise" / "noise" / "floor-1.wav"
    _write_wav(floor_noise_path, samples=[0, 0, 1, -1])
    import_dir.mkdir(parents=True, exist_ok=True)
    (import_dir / "import.json").write_text(
        json.dumps(
            {
                "role_id": "MEGAERA",
                "imported": [
                    {"segment_id": "0_1_1", "floor_noise_id": "floor-1"},
                    {"segment_id": "0_1_2"},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = AudioCleanupService(paths_config=cfg, tool_checker=FakeAudioToolChecker()).prepare(role="MEGAERA")

    assert {item.batch_id for item in result} == {
        "MEGAERA-gentle_voice_cleanup",
        "MEGAERA-gentle_voice_cleanup-floor-1",
    }


def test_audio_cleanup_service_uses_timestamp_floor_noise_fallback(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav", samples=[0, 1200, -1200, 0])
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_2.wav", samples=[0, 1300, -1300, 0])
    import_dir = cfg.build_dir / "linerecorder" / "imports" / "20260518T010101Z"
    floor_1 = import_dir / "floor_noise" / "noise" / "floor-1.wav"
    floor_2 = import_dir / "floor_noise" / "noise" / "floor-2.wav"
    _write_wav(floor_1, samples=[0, 0, 1, -1])
    _write_wav(floor_2, samples=[0, 0, 2, -2])
    import_dir.mkdir(parents=True, exist_ok=True)
    (import_dir / "import.json").write_text(
        json.dumps(
            {
                "role_id": "MEGAERA",
                "floor_noise_recordings": [
                    {
                        "id": "floor-1",
                        "artifact_path": paths.display_path(floor_1),
                        "recorded_at": "2026-05-18T10:00:00Z",
                    },
                    {
                        "id": "floor-2",
                        "artifact_path": paths.display_path(floor_2),
                        "recorded_at": "2026-05-18T11:00:00Z",
                    },
                ],
                "imported": [
                    {"segment_id": "0_1_1", "recorded_at": "2026-05-18T10:30:00Z"},
                    {"segment_id": "0_1_2", "recorded_at": "2026-05-18T11:30:00Z"},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = AudioCleanupService(paths_config=cfg, tool_checker=FakeAudioToolChecker()).prepare(role="MEGAERA")

    assert {item.batch_id for item in result} == {
        "MEGAERA-gentle_voice_cleanup-floor-1",
        "MEGAERA-gentle_voice_cleanup-floor-2",
    }


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


class FakeAudioToolChecker:
    def require_audio_tools(self) -> FfmpegInstallation:
        return FfmpegInstallation(
            ffmpeg_path=Path("/usr/bin/ffmpeg"),
            ffprobe_path=Path("/usr/bin/ffprobe"),
            source="PATH",
            config_path=None,
            filters=frozenset({"loudnorm", "atrim", "asetpts", "adeclick", "deesser", "afftdn"}),
        )
