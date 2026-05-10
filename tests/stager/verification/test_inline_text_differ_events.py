from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from diff_context import DiffContext
from diff_walker import DiffWalker
from inline_text_differ import InlineTextDiffer


def _context(differ: InlineTextDiffer, expected: str, actual: str) -> DiffContext:
    diffs, id_to_token, expected_tokens, expected_types, actual_tokens, actual_types = differ._diffs_for_texts(
        expected,
        actual,
    )
    expected_word_indices = differ._build_word_indices(expected_types)
    return DiffContext(
        diffs=diffs,
        id_to_token=id_to_token,
        expected_tokens=expected_tokens,
        expected_types=expected_types,
        actual_tokens=actual_tokens,
        actual_types=actual_types,
        expected_word_indices=expected_word_indices,
        segment_id=None,
    )


def test_diff_walker_emits_replace() -> None:
    differ = InlineTextDiffer()
    context = _context(differ, "one two", "one too")
    events = list(DiffWalker(context))

    assert [event.op for event in events] == ["match", "replace"]
    assert events[1].expected is not None
    assert events[1].actual is not None
    assert events[1].expected.text() == "two"
    assert events[1].actual.text() == "too"


def test_diff_walker_emits_insert() -> None:
    differ = InlineTextDiffer()
    context = _context(differ, "one two", "one two three")
    events = list(DiffWalker(context))

    assert [event.op for event in events] == ["match", "insert"]
    assert events[1].actual is not None
    assert events[1].actual.text().strip() == "three"
