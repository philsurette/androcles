import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from block import RoleBlock
from block_id import BlockId
from segment import DirectionSegment, SpeechSegment


def split_segments(text: str, *, part: int | None = 1, block_no: int = 1, role: str = "CALL BOY"):
    """Helper to split text into RoleBlock segments with predictable ids."""
    return RoleBlock.split_block_segments(text, BlockId(part, block_no), role)


def test_roleblock_split_preserves_inline_direction_and_exclamations() -> None:
    segments = split_segments("(_sneers derisively_)!!")

    assert isinstance(segments[0], DirectionSegment)
    assert segments[0].text == "(_sneers derisively_)"
    assert segments[0].segment_id.segment_no == 1

    assert isinstance(segments[1], SpeechSegment)
    assert segments[1].text == "!!"
    assert segments[1].role == "CALL BOY"
    assert segments[1].segment_id.segment_no == 2


def test_roleblock_split_exclamation_then_speech_stays_together() -> None:
    text = "(_groans_)!!! Then is nobody ever killed except us poor—"
    segments = split_segments(text)

    assert isinstance(segments[0], DirectionSegment)
    assert segments[0].text == "(_groans_)"
    assert isinstance(segments[1], SpeechSegment)
    assert segments[1].text == "!!! Then is nobody ever killed except us poor—"
    assert segments[1].role == "CALL BOY"


@pytest.mark.parametrize("punct", [".", "!", ",", ":"])
def test_roleblock_split_trivial_punctuation_stays_with_direction(punct: str) -> None:
    text = f"(_sneers derisively_){punct}"
    segments = split_segments(text)

    assert len(segments) == 1
    assert isinstance(segments[0], DirectionSegment)
    assert segments[0].text == text
    assert segments[0].segment_id.segment_no == 1


def test_roleblock_split_exclamations_and_questions_become_segment() -> None:
    text = "(_sneers derisively_)!?!"
    segments = split_segments(text)

    assert isinstance(segments[0], DirectionSegment)
    assert segments[0].text == "(_sneers derisively_)"
    assert isinstance(segments[1], SpeechSegment)
    assert segments[1].text == "!?!"
    assert segments[1].role == "CALL BOY"
