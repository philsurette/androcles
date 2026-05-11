from __future__ import annotations

import wave
from pathlib import Path

import pytest

from stager.playbook.playbook_audio_packager import PlaybookAudioPackager


def _write_wav(path: Path, duration_ms: int = 100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_rate = 8_000
    frame_count = int(frame_rate * duration_ms / 1000)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(frame_rate)
        wav.writeframes(b"\x00\x00" * frame_count)


def test_packager_copies_wav_and_returns_manifest_path(tmp_path: Path) -> None:
    app_dir = tmp_path / "app"
    source_path = tmp_path / "source" / "0_1_1.wav"
    destination_dir = app_dir / "audio" / "segments" / "ANDROCLES"
    _write_wav(source_path)

    packaged = PlaybookAudioPackager(app_dir=app_dir).package(source_path, destination_dir)

    assert packaged.path == destination_dir / "0_1_1.wav"
    assert packaged.path.read_bytes() == source_path.read_bytes()
    assert packaged.manifest_path.as_posix() == "audio/segments/ANDROCLES/0_1_1.wav"


def test_packager_exports_mp3_with_ffmpeg_backed_pydub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_dir = tmp_path / "app"
    source_path = tmp_path / "source" / "0_1_1.wav"
    destination_dir = app_dir / "audio" / "segments" / "ANDROCLES"
    _write_wav(source_path)

    class FakeAudio:
        def export(self, destination: Path, format: str, bitrate: str) -> None:
            assert format == "mp3"
            assert bitrate == "128k"
            destination.write_bytes(b"fake mp3")

    class FakeAudioSegment:
        @staticmethod
        def from_file(path: Path) -> FakeAudio:
            assert path == source_path
            return FakeAudio()

    monkeypatch.setattr(
        "stager.playbook.playbook_audio_packager.AudioSegment",
        FakeAudioSegment,
    )

    packaged = PlaybookAudioPackager(app_dir=app_dir, audio_format="mp3").package(
        source_path,
        destination_dir,
    )

    assert packaged.path == destination_dir / "0_1_1.mp3"
    assert packaged.path.read_bytes() == b"fake mp3"
    assert packaged.manifest_path.as_posix() == "audio/segments/ANDROCLES/0_1_1.mp3"


def test_packager_rejects_unsupported_audio_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="audio_format must be one of: wav, mp3"):
        PlaybookAudioPackager(app_dir=tmp_path / "app", audio_format="flac")
