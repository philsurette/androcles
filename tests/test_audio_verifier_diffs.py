from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from audio_verifier_diff_builder import AudioVerifierDiffBuilder
from extra_audio_diff import ExtraAudioDiff
from match_audio_diff import MatchAudioDiff
from missing_audio_diff import MissingAudioDiff
from inline_text_differ import InlineTextDiffer


def test_missing_orders_between_matched_segments() -> None:
    results = {
        "segments": [
            {
                "segment_index": 0,
                "segment_id": "1_1_1",
                "status": "matched",
                "expected_text": "hello",
                "matched_audio_text": "hello",
                "matched_audio_start": 0.0,
                "matched_audio_end": 1.0,
                "inline_diff": "hello",
            },
            {
                "segment_index": 1,
                "segment_id": "1_1_2",
                "status": "missing",
                "expected_text": "missing",
                "matched_audio_text": "",
                "matched_audio_start": None,
                "matched_audio_end": None,
            },
            {
                "segment_index": 2,
                "segment_id": "1_1_3",
                "status": "matched",
                "expected_text": "world",
                "matched_audio_text": "world",
                "matched_audio_start": 10.0,
                "matched_audio_end": 11.0,
                "inline_diff": "world",
            },
        ],
        "extra_audio": [],
    }

    diffs = AudioVerifierDiffBuilder().build(results)

    assert isinstance(diffs[0], MatchAudioDiff)
    assert isinstance(diffs[1], MissingAudioDiff)
    assert isinstance(diffs[2], MatchAudioDiff)


def test_missing_first_appears_at_top() -> None:
    results = {
        "segments": [
            {
                "segment_index": 0,
                "segment_id": "1_1_1",
                "status": "missing",
                "expected_text": "first",
                "matched_audio_text": "",
                "matched_audio_start": None,
                "matched_audio_end": None,
            },
            {
                "segment_index": 1,
                "segment_id": "1_1_2",
                "status": "matched",
                "expected_text": "second",
                "matched_audio_text": "second",
                "matched_audio_start": 5.0,
                "matched_audio_end": 6.0,
                "inline_diff": "second",
            },
        ],
        "extra_audio": [
            {
                "matched_audio_start": 1.0,
                "matched_audio_end": 1.5,
                "recognized_text": "extra",
            }
        ],
    }

    diffs = AudioVerifierDiffBuilder().build(results)

    assert isinstance(diffs[0], MissingAudioDiff)
    assert any(isinstance(diff, ExtraAudioDiff) for diff in diffs)


def test_rows_include_segment_id() -> None:
    diff = MatchAudioDiff(
        segment_id="1_2_3",
        expected="alpha",
        heard="alpha",
        diff="alpha",
        match_quality=0,
        offset_ms=0,
        length_ms=1000,
    )
    row = diff.to_row()

    assert row["id"] == "1_2_3"


def test_inline_text_differ_ignores_apostrophes_and_case() -> None:
    differ = InlineTextDiffer()
    diff = differ.diff("Here’s a Test.", "Here's a test")

    assert diff.inline_diff == "Here’s a Test."
    assert differ.count_diffs("Here’s a Test.", "Here's a test") == 0


def test_inline_text_differ_ignores_punctuation_changes() -> None:
    differ = InlineTextDiffer()
    expected = "One, two; three: four."
    actual = "One two three four"

    diff = differ.diff(expected, actual)

    assert diff.inline_diff == expected
    assert differ.count_diffs(expected, actual) == 0


def test_inline_text_differ_ignores_quotes_and_question_runs() -> None:
    differ = InlineTextDiffer()
    expected = 'He said, "What?!??"'
    actual = "he said what."

    diff = differ.diff(expected, actual)

    assert diff.inline_diff == expected
    assert differ.count_diffs(expected, actual) == 0


def test_inline_text_differ_ignores_dash_sequences() -> None:
    differ = InlineTextDiffer()
    expected = "Wait -- what --- now."
    actual = "wait. what: now"

    diff = differ.diff(expected, actual)

    assert diff.inline_diff == expected
    assert differ.count_diffs(expected, actual) == 0


def test_inline_text_differ_ignores_missing_apostrophes() -> None:
    differ = InlineTextDiffer()
    expected = "Well, the lion’s ate him."
    actual = "Well, the lions ate him."

    diff = differ.diff(expected, actual)

    assert diff.inline_diff == expected
    assert differ.count_diffs(expected, actual) == 0


def test_inline_text_differ_relaxes_known_names() -> None:
    differ = InlineTextDiffer(name_tokens={"ferrovius", "call", "boy"})
    expected = "Ferrovius went to the Call Boy."
    actual = "Ferovius went to the Callboy."

    diff = differ.diff(expected, actual)

    assert diff.inline_diff == expected
    assert differ.count_diffs(expected, actual) == 0
