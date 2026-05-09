from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import paths


def test_display_path_uses_project_relative_paths() -> None:
    assert paths.display_path(ROOT / "build" / "fairies" / "out.md") == "build/fairies/out.md"


def test_display_location_formats_clickable_location() -> None:
    assert paths.display_location(ROOT / "plays" / "fairies" / "play.txt", 213, 1) == "plays/fairies/play.txt:213:1"
