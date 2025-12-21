
import pytest

from play import (
    DirectionSegment,
    Play,
)
from segment import DescriptionSegment, MetaSegment, SpeechSegment
from segment_id import SegmentId
from block_id import BlockId
from block import DescriptionBlock, MetaBlock, RoleBlock    

def build_play(sequence):
    """Helper to build a PlayText from a list of (part, block_no, role)."""
    items = []
    for part, block_no, role in sequence:
        items.append(
            RoleBlock(
                block_id=BlockId(part, block_no),
                role=role,
                text="",
                segments=[SpeechSegment(segment_id=SegmentId(BlockId(part, block_no), 1), text="", role=role)],
            )
        )
    return Play(items)


def test_preceding_roles_basic():
    pt = build_play([(0, 1, "A"), (0, 2, "B"), (0, 3, "C")])
    assert pt.getPrecedingRoles(BlockId(0, 3), num_preceding=2) == ["A", "B"]

def test_preceding_roles_most_recent():
    pt = build_play([(0, 1, "A"), (0, 2, "B"), (0, 3, "C"), (0, 4, "D")])
    assert pt.getPrecedingRoles(BlockId(0, 4), num_preceding=2) == ["B", "C"]

def test_preceding_roles_distinct():
    pt = build_play([(0, 1, "A"), (0, 2, "A"), (0, 3, "B"), (0, 4, "A")])
    assert pt.getPrecedingRoles(BlockId(0, 4), num_preceding=2) == ["A", "B"]
    assert pt.getPrecedingRoles(BlockId(0, 4), num_preceding=3) == ["A", "B"]

def test_preceding_roles_ignores_meta_by_default():
    pt = build_play([(0, 1, "A"), (0, 2, "_NARRATOR"), (0, 3, "B")])
    assert pt.getPrecedingRoles(BlockId(0, 3), num_preceding=2) == ["A"]

def test_preceding_roles_includes_meta_when_requested():
    pt = build_play([(0, 1, "A"), (0, 2, "_NARRATOR"), (0, 3, "B"), (0, 4, "_DIRECTOR")])
    assert pt.getPrecedingRoles(BlockId(0, 4), num_preceding=3, include_meta_roles=True) == [
        "A",
        "_NARRATOR",
        "B",
    ]

def test_preceding_roles_limit_part():
    pt = build_play([(0, 1, "A"), (1, 1, "B"), (1, 2, "C")])
    # Should ignore part 0 when limit_to_current_part is True
    assert pt.getPrecedingRoles(BlockId(1, 2), num_preceding=2, limit_to_current_part=True) == ["B"]
    # When not limiting, includes previous part roles
    assert pt.getPrecedingRoles(BlockId(1, 2), num_preceding=2, limit_to_current_part=False) == ["A", "B"]


def test_preceding_roles_fewer_than_requested():
    pt = build_play([(0, 1, "A")])
    assert pt.getPrecedingRoles(BlockId(0, 1), num_preceding=2) == []
    assert pt.getPrecedingRoles(BlockId(0, 1), num_preceding=1) == []


def test_preceding_roles_exact():
    pt = build_play([(0, 1, "A"), (0, 2, "B")])
    assert pt.getPrecedingRoles(BlockId(0, 2), num_preceding=1) == ["A"]


def test_block_id_next_previous():
    bid = BlockId(1, 5)
    assert bid.nextId() == BlockId(1, 6)
    assert bid.previousId() == BlockId(1, 4)


def test_block_id_previous_none_for_zero():
    assert BlockId(2, 0).previousId() is None


def test_block_id_equality_and_hash():
    a = BlockId(1, 2)
    b = BlockId(1, 2)
    c = BlockId(1, 3)
    assert a == b
    assert hash(a) == hash(b)
    assert a != c


def test_block_lookup_by_id():
    pt = build_play([(0, 1, "A"), (0, 2, "B")])
    assert pt.block_for_id(BlockId(0, 1)).role == "A"
    assert pt.block_for_id(BlockId(0, 99)) is None


def test_to_index_entries_matches_block_order_and_inline_dirs():
    meta_id = BlockId(None, 1)
    meta_block = MetaBlock(
        block_id=meta_id,
        text="::intro::",
        segments=[MetaSegment(segment_id=SegmentId(meta_id, 1), text="intro")],
    )

    role_id = BlockId(0, 1)
    role_block = RoleBlock(
        block_id=role_id,
        role="A",
        text="Hello",
        segments=[SpeechSegment(segment_id=SegmentId(role_id, 1), text="Hello", role="A")],
    )

    role_with_dir_id = BlockId(0, 2)
    role_with_dir_block = RoleBlock(
        block_id=role_with_dir_id,
        role="B",
        text="(_wave_) Hi",
        segments=[
            DirectionSegment(segment_id=SegmentId(role_with_dir_id, 1), text="(_wave_)"),
            SpeechSegment(segment_id=SegmentId(role_with_dir_id, 2), text="Hi", role="B"),
        ],
    )

    desc_id = BlockId(0, 3)
    desc_block = DescriptionBlock(
        block_id=desc_id,
        text="[[desc]]",
        segments=[DescriptionSegment(segment_id=SegmentId(desc_id, 1), text="desc")],
    )

    play = Play([meta_block, role_block, role_with_dir_block, desc_block])

    assert play.to_index_entries() == [
        (None, 1, "_NARRATOR"),  # meta block
        (0, 1, "A"),  # plain role block
        (0, 2, "_NARRATOR"),  # inline direction emitted as narrator first
        (0, 2, "B"),
        (0, 3, "_NARRATOR"),  # description block
    ]
