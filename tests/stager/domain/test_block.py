import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from stager.domain.block import RoleBlock
from stager.domain.block_id import BlockId
from stager.domain.segment import DirectionSegment, SimultaneousSegment, SpeechSegment


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


def test_roleblock_parse_keeps_leading_i_ellipsis_as_speech() -> None:
    block = RoleBlock.parse(
        "CHRISTINE. I... I've had such a wonderful time.",
        current_part=5,
        block_counter=30,
        meta_counters={},
    )

    assert isinstance(block, RoleBlock)
    assert block.role_names == ["CHRISTINE"]
    assert block.text == "I... I've had such a wonderful time."
    assert len(block.segments) == 1
    assert isinstance(block.segments[0], SpeechSegment)
    assert block.segments[0].role == "CHRISTINE"
    assert block.segments[0].text == "I... I've had such a wonderful time."


def test_roleblock_markdown_includes_rendered_block_id_prefix() -> None:
    block = RoleBlock.parse(
        "CHRISTINE. This is Christine Canfield.",
        current_part=0,
        block_counter=1,
        meta_counters={},
    )

    assert isinstance(block, RoleBlock)
    assert block.to_markdown(render_id=True) == "0.2 **CHRISTINE**: This is Christine Canfield."


def test_roleblock_parse_explicit_comma_roles_as_simultaneous() -> None:
    block = RoleBlock.parse(
        "ANDROCLES,MEGAERA. Together now",
        current_part=1,
        block_counter=3,
        meta_counters={},
    )

    assert isinstance(block, RoleBlock)
    assert block.role_names == ["ANDROCLES", "MEGAERA"]
    assert len(block.segments) == 1
    assert isinstance(block.segments[0], SimultaneousSegment)
    assert block.segments[0].roles == ["ANDROCLES", "MEGAERA"]
    assert block.segments[0].text == "Together now"


def test_roleblock_parse_explicit_group_roles_as_simultaneous() -> None:
    block = RoleBlock.parse(
        "GLADIATORS[GLADIATOR-1,GLADIATOR-2]. Hail, Caesar!",
        current_part=2,
        block_counter=73,
        meta_counters={},
    )

    assert isinstance(block, RoleBlock)
    assert block.role_names == ["GLADIATOR-1", "GLADIATOR-2"]
    assert block.callout == "GLADIATORS"
    assert len(block.segments) == 1
    assert isinstance(block.segments[0], SimultaneousSegment)
    assert block.segments[0].roles == ["GLADIATOR-1", "GLADIATOR-2"]
    assert block.segments[0].text == "Hail, Caesar!"
