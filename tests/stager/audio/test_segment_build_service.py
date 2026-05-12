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


def test_build_reports_recording_export_and_split_progress(tmp_path: Path, monkeypatch) -> None:
    events: list[tuple[str, int | str | None]] = []

    class FakeProgressReporter:
        def start(self, total: int, description: str) -> None:
            events.append(("start", total))
            events.append(("description", description))

        def advance(self, description: str | None = None) -> None:
            events.append(("advance", description))

        def finish(self, description: str | None = None) -> None:
            events.append(("finish", description))

    class FakeExporter:
        def __init__(self, *, paths):
            self.paths = paths

        def export_recordings(self, *, force: bool = False, role: str | None = None):
            return None

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

        def split_target_count(self, *, role_filter=None):
            return 1

        def split_all(self, *, part_filter=None, role_filter=None):
            self.kwargs["progress_reporter"].advance("Split DOYLE")
            return None

    monkeypatch.setattr(segment_build_service, "AudacityRecordingExporter", FakeExporter)
    monkeypatch.setattr(segment_build_service, "BuildTypeResolver", FakeBuildTypeResolver)
    monkeypatch.setattr(segment_build_service, "ProductionPlayLoader", FakeProductionPlayLoader)
    monkeypatch.setattr(segment_build_service, "PlaySplitter", FakePlaySplitter)

    SegmentBuildService(paths=_config(tmp_path), progress_reporter=FakeProgressReporter()).build(
        role="DOYLE",
        force=True,
    )

    assert events == [
        ("start", 2),
        ("description", "Exporting recordings"),
        ("advance", "Splitting segments"),
        ("advance", "Split DOYLE"),
        ("finish", "Split segments"),
    ]
