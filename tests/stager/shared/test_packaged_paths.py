from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from stager.shared import paths


def test_default_root_uses_source_checkout_root() -> None:
    assert paths.ROOT == paths.project_root() / "src"


def test_packaged_default_root_uses_current_working_directory(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(paths, "sys", SimpleNamespace(frozen=True))

    assert paths._default_root() == tmp_path / "src"
