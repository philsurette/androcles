import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import blocks


def test_split_block_segments_preserves_inline_direction_and_exclamations() -> None:
    text = "(_sneers derisively_)!!"
    segments = blocks.split_block_segments(text)
    assert segments == [
        "(_sneers derisively_)",
        "!!",
    ]

def test_split_block_segments_exclamation_then_speech_stays_together() -> None:
    text = "(_groans_)!!! Then is nobody ever killed except us poor—"
    segments = blocks.split_block_segments(text)
    assert segments == [
        "(_groans_)",
        "!!! Then is nobody ever killed except us poor—",
    ]

def test_split_block_segments_trivial_punctuation_stays_with_direction_period() -> None:
    text = "(_sneers derisively_)."
    segments = blocks.split_block_segments(text)
    assert segments == [
        "(_sneers derisively_).",
    ]

def test_split_block_segments_trivial_punctuation_stays_with_direction_exclamation() -> None:
    text = "(_sneers derisively_)!"
    segments = blocks.split_block_segments(text)
    assert segments == [
        "(_sneers derisively_)!",
    ]

def test_split_block_segments_trivial_punctuation_stays_with_direction_comma() -> None:
    text = "(_sneers derisively_),"
    segments = blocks.split_block_segments(text)
    assert segments == [
        "(_sneers derisively_),",
    ]

def test_split_block_segments_trivial_punctuation_stays_with_direction_colon() -> None:
    text = "(_sneers derisively_):"
    segments = blocks.split_block_segments(text)
    assert segments == [
        "(_sneers derisively_):",
    ]

def test_split_block_segments_exclamations_and_questions_become_segment() -> None:
    text = "(_sneers derisively_)!?!"
    segments = blocks.split_block_segments(text)
    assert segments == [
        "(_sneers derisively_)",
        "!?!",
    ]
