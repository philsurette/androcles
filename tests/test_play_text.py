import pytest

from play_text import PlayText, BlockId, RoleBlock


def build_play_text(sequence):
    """Helper to build a PlayText from a list of (part, block_no, role)."""
    items = []
    for part, block_no, role in sequence:
        items.append(RoleBlock(block_id=BlockId(part, block_no), role=role, text="", segments=[]))
    return PlayText(items)


def test_preceding_roles_basic():
    pt = build_play_text([(0, 1, "A"), (0, 2, "B"), (0, 3, "C")])
    assert pt.getPrecedingRoles(BlockId(0, 3), num_preceding=2) == ["A", "B"]

def test_preceding_roles_most_recent():
    pt = build_play_text([(0, 1, "A"), (0, 2, "B"), (0, 3, "C"), (0, 4, "D")])
    assert pt.getPrecedingRoles(BlockId(0, 4), num_preceding=2) == ["B", "C"]

def test_preceding_roles_distinct():
    pt = build_play_text([(0, 1, "A"), (0, 2, "A"), (0, 3, "B"), (0, 4, "A")])
    assert pt.getPrecedingRoles(BlockId(0, 4), num_preceding=2) == ["A", "B"]
    assert pt.getPrecedingRoles(BlockId(0, 4), num_preceding=3) == ["A", "B"]

def test_preceding_roles_ignores_meta_by_default():
    pt = build_play_text([(0, 1, "A"), (0, 2, "_NARRATOR"), (0, 3, "B")])
    assert pt.getPrecedingRoles(BlockId(0, 3), num_preceding=2) == ["A"]

def test_preceding_roles_includes_meta_when_requested():
    pt = build_play_text([(0, 1, "A"), (0, 2, "_NARRATOR"), (0, 3, "B"), (0, 4, "_DIRECTOR")])
    assert pt.getPrecedingRoles(BlockId(0, 4), num_preceding=3, include_meta_roles=True) == [
        "A",
        "_NARRATOR",
        "B",
    ]

def test_preceding_roles_limit_part():
    pt = build_play_text([(0, 1, "A"), (1, 1, "B"), (1, 2, "C")])
    # Should ignore part 0 when limit_to_current_part is True
    assert pt.getPrecedingRoles(BlockId(1, 2), num_preceding=2, limit_to_current_part=True) == ["B"]
    # When not limiting, includes previous part roles
    assert pt.getPrecedingRoles(BlockId(1, 2), num_preceding=2, limit_to_current_part=False) == ["A", "B"]


def test_preceding_roles_fewer_than_requested():
    pt = build_play_text([(0, 1, "A")])
    assert pt.getPrecedingRoles(BlockId(0, 1), num_preceding=2) == []
    assert pt.getPrecedingRoles(BlockId(0, 1), num_preceding=1) == []


def test_preceding_roles_exact():
    pt = build_play_text([(0, 1, "A"), (0, 2, "B")])
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
    pt = build_play_text([(0, 1, "A"), (0, 2, "B")])
    assert pt.block_for_id(BlockId(0, 1)).role == "A"
    assert pt.block_for_id(BlockId(0, 99)) is None
