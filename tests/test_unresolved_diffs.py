from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from unresolved_diffs import UnresolvedDiffs


def test_unresolved_diffs_write_flow_list(tmp_path) -> None:
    diffs = UnresolvedDiffs()
    diffs.add("Spintho", "spinto")

    path = tmp_path / "unresolved.yaml"
    diffs.write(path)

    content = path.read_text(encoding="utf-8")
    assert "equivalencies:" in content
    assert "Spintho: [spinto]" in content


def test_unresolved_diffs_quote_keys_with_spaces(tmp_path) -> None:
    diffs = UnresolvedDiffs()
    diffs.add("They’re ladies of rank.", "their ladies are frank", segment_id="2_14_1")

    path = tmp_path / "unresolved.yaml"
    diffs.write(path)

    content = path.read_text(encoding="utf-8")
    assert "\"Theyre ladies of rank@2_14_1\": [their ladies are frank]" in content


def test_unresolved_diffs_strip_punctuation(tmp_path) -> None:
    diffs = UnresolvedDiffs()
    diffs.add(". Iscariot!", "is scary it", segment_id="2_33_1")

    path = tmp_path / "unresolved.yaml"
    diffs.write(path)

    content = path.read_text(encoding="utf-8")
    assert "Iscariot@2_33_1: [is scary it]" in content
