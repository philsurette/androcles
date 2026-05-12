from __future__ import annotations

from pathlib import Path

from stager.audio import segment_build_service
from stager.audio.segment_build_service import SegmentBuildService
from stager.shared.paths import PathConfig


def _config(tmp_path: Path) -> PathConfig:
    return PathConfig(
        play_name="test",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )


def test_build_passes_force_and_role_to_audacity_exporter(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[bool, str | None]] = []

    class FakeExporter:
        def __init__(self, *, paths):
            self.paths = paths

        def export_recordings(self, *, force: bool = False, role: str | None = None):
            calls.append((force, role))

    class FakeBuildTypeResolver:
        def __init__(self, **kwargs):
            pass

        def resolve(self):
            return "custom"

    class FakeProductionPlayLoader:
        def __init__(self, **kwargs):
            pass

        def load(self):
            return object()

    class FakePlaySplitter:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def split_all(self, *, part_filter=None, role_filter=None):
            return None

    monkeypatch.setattr(segment_build_service, "AudacityRecordingExporter", FakeExporter)
    monkeypatch.setattr(segment_build_service, "BuildTypeResolver", FakeBuildTypeResolver)
    monkeypatch.setattr(segment_build_service, "ProductionPlayLoader", FakeProductionPlayLoader)
    monkeypatch.setattr(segment_build_service, "PlaySplitter", FakePlaySplitter)

    SegmentBuildService(paths=_config(tmp_path)).build(role="DOYLE", force=True)

    assert calls == [(True, "DOYLE")]
