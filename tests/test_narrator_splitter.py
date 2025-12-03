import pytest

from narrator_splitter import NarratorSplitter
from play_text import NarratorRole, RoleBlock

from segment import DirectionSegment
from segment_id import SegmentId
from block_id import BlockId
from block import RoleBlock 

class DummyPlay:
    def __init__(self, role):
        self.role = role
        self.blocks = role.blocks

    def getRole(self, name):
        return self.role if name == "_NARRATOR" else None

    def __iter__(self):
        return iter(self.blocks)


def _block(part_id, block_no, texts):
    bid = BlockId(part_id, block_no)
    segments = [DirectionSegment(segment_id=SegmentId(bid, idx + 1), text=t) for idx, t in enumerate(texts)]
    return RoleBlock(block_id=bid, role="_NARRATOR", text=" ".join(texts), segments=segments)


def test_assemble_segment_ids_filters_punctuation():
    role = NarratorRole(
        name="_NARRATOR",
        blocks=[_block(None, 1, ["Intro", ".", "More"]), _block(1, 2, [",", "Line", ";"])],
    )
    splitter = NarratorSplitter(play_text=DummyPlay(role))

    segments = splitter.expected_ids()

    ids = [str(seg.segment_id) for seg in segments]
    assert ids == ["_1_1", "_1_2", "_1_3", "1_2_1", "1_2_2", "1_2_3"]


def test_assemble_segment_ids_respects_part_filter():
    role = NarratorRole(
        name="_NARRATOR",
        blocks=[_block(None, 1, ["Intro"]), _block(1, 2, ["Part1"]), _block(2, 3, ["Part2"])],
    )
    splitter = NarratorSplitter(play_text=DummyPlay(role))

    segments = splitter.expected_ids(part_filter="1")

    ids = [splitter._segment_id_str(seg) for seg in segments]
    assert ids == ["1_2_1"]
