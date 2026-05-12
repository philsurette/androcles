from __future__ import annotations

from pathlib import Path

from stager.cues import cue_build_service
from stager.cues.cue_build_service import CueBuildService
from stager.domain.play import Role
from stager.shared.paths import PathConfig


def _config(tmp_path: Path) -> PathConfig:
    return PathConfig(
        play_name="test",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )


def test_cue_build_service_reports_role_progress(tmp_path: Path, monkeypatch) -> None:
    events: list[tuple[str, int | str | None]] = []
    built_roles: list[str] = []

    class FakeProgressReporter:
        def start(self, total: int, description: str) -> None:
            events.append(("start", total))
            events.append(("description", description))

        def advance(self, description: str | None = None) -> None:
            events.append(("advance", description))

        def finish(self, description: str | None = None) -> None:
            events.append(("finish", description))

    class FakeProductionPlayLoader:
        def __init__(self, **kwargs):
            pass

        def load(self):
            return type("FakePlay", (), {"roles": [Role("ANDROCLES"), Role("MEGAERA")]})()

    class FakeCueBuilder:
        def __init__(self, *args, **kwargs):
            pass

        def build_cues(self, role: str) -> None:
            built_roles.append(role)

    monkeypatch.setattr(cue_build_service, "ProductionPlayLoader", FakeProductionPlayLoader)
    monkeypatch.setattr(cue_build_service, "CueBuilder", FakeCueBuilder)

    CueBuildService(paths=_config(tmp_path), progress_reporter=FakeProgressReporter()).build()

    assert built_roles == ["ANDROCLES", "MEGAERA", "_NARRATOR"]
    assert events == [
        ("start", 3),
        ("description", "Building cue files"),
        ("advance", "Built cues for ANDROCLES"),
        ("advance", "Built cues for MEGAERA"),
        ("advance", "Built cues for _NARRATOR"),
        ("finish", "Built cue files"),
    ]
