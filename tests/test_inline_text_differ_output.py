from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from inline_text_differ import InlineTextDiffer


def test_windowed_diffs_include_context() -> None:
    differ = InlineTextDiffer(window_before=1, window_after=1)
    expected = "The quick brown fox jumps over the lazy dog."
    actual = "The quick brown fox jump over the lazy dog."

    diff = differ.diff(expected, actual)

    assert diff.inline_diff == "The quick brown fox [jump/jumps] over the lazy dog."
    assert diff.windowed_diffs == ["fox [jump/jumps] over"]


def test_replacement_pairs_only_word_replacements() -> None:
    differ = InlineTextDiffer()
    replacements = differ.replacement_pairs("The quick fox.", "The fast fox.")

    assert len(replacements) == 1
    assert replacements[0].expected == "quick"
    assert replacements[0].actual == "fast"


def test_replacement_pairs_ignore_inserts() -> None:
    differ = InlineTextDiffer()
    replacements = differ.replacement_pairs("The quick fox.", "The quick fox jumps.")

    assert replacements == []
