from __future__ import annotations

import os
from pathlib import Path

from stager.audio.audacity_recording_exporter import AudacityRecordingExporter
from stager.shared.paths import PathConfig


class FakeAudacityClient:
    def __init__(self, exported: list[str]) -> None:
        self.exported = exported
        self.current_project = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def open_project(self, *, project):
        self.current_project = project
        return self

    def export_project(self):
        self.exported.append(self.current_project.path.stem)


class FakeAudacity:
    def __init__(self) -> None:
        self.exported: list[str] = []

    def open(self):
        return FakeAudacityClient(self.exported)


def _config(tmp_path: Path) -> PathConfig:
    return PathConfig(
        play_name="test",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )


def _touch(path: Path, mtime: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(path.name, encoding="utf-8")
    os.utime(path, (mtime, mtime))


def test_export_recordings_skips_up_to_date_exports(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    _touch(cfg.recordings_dir / "DOYLE.aup3", 100)
    _touch(cfg.recordings_dir / "DOYLE.wav", 200)
    audacity = FakeAudacity()

    AudacityRecordingExporter(paths=cfg, audacity=audacity).export_recordings()

    assert audacity.exported == []


def test_export_recordings_force_exports_up_to_date_exports(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    aup3_path = cfg.recordings_dir / "DOYLE.aup3"
    wav_path = cfg.recordings_dir / "DOYLE.wav"
    _touch(aup3_path, 100)
    _touch(wav_path, 200)
    audacity = FakeAudacity()

    AudacityRecordingExporter(paths=cfg, audacity=audacity).export_recordings(force=True)

    assert audacity.exported == ["DOYLE"]
    assert not wav_path.exists()


def test_export_recordings_role_limits_forced_export(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    _touch(cfg.recordings_dir / "DOYLE.aup3", 100)
    _touch(cfg.recordings_dir / "DOYLE.wav", 200)
    _touch(cfg.recordings_dir / "LILLIAN.aup3", 100)
    _touch(cfg.recordings_dir / "LILLIAN.wav", 200)
    audacity = FakeAudacity()

    AudacityRecordingExporter(paths=cfg, audacity=audacity).export_recordings(force=True, role="DOYLE")

    assert audacity.exported == ["DOYLE"]
