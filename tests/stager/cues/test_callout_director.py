from pathlib import Path
import pytest

from stager.domain.play import Play
from stager.domain.block_id import BlockId
from stager.domain.block import RoleBlock, DescriptionBlock
from stager.domain.segment import DirectionSegment
from stager.cues.callout_director import (
    NoCalloutDirector,
    RoleCalloutDirector,
    ConversationAwareCalloutDirector,
)
from stager.audiobook.clip import CalloutClip


def build_play(seq):
    """Helper to build a PlayText from a list of tuples describing blocks."""
    items = []
    for entry in seq:
        kind = entry[0]
        part = entry[1]
        block_no = entry[2]
        if kind == "role":
            role = entry[3]
            segments = entry[4] if len(entry) > 4 else []
            items.append(
                RoleBlock(
                    block_id=BlockId(part, block_no),
                    role_names=[role],
                    callout=role,
                    text="",
                    segments=segments,
                )
            )
        elif kind == "desc":
            text = entry[3]
            items.append(DescriptionBlock(block_id=BlockId(part, block_no), text=text, segments=[]))
    return Play(blocks=items)


class TestNoCalloutDirector:
    def test_no_callout(self):
        pt = build_play([("role", 0, 1, "A")])
        director = NoCalloutDirector(pt)
        assert director.calloutForBlock(BlockId(0, 1)) is None


class TestRoleCalloutDirector:
    def test_calloutForBlock_role(self):
        pt = build_play([("role", 0, 1, "A")])
        director = RoleCalloutDirector(pt)
        director._build_callout_clip = lambda role: CalloutClip(
            path=Path("/tmp/fake.wav"), text="", role="_NARRATOR", clip_id=role, length_ms=0, offset_ms=0
        )
        clip = director.calloutForBlock(BlockId(0, 1))
        assert isinstance(clip, CalloutClip)
        assert clip.clip_id == "A"

    def test_calloutForBlock_description(self):
        pt = build_play([("desc", 0, 1, 'description text')])
        director = RoleCalloutDirector(pt)
        assert director.calloutForBlock(BlockId(0, 1)) == None

class TestConversationAwareCalloutDirector:
    def test_first_two_roles(self):
        pt = build_play([
            ("role", 0, 1, "A"),
            ("role", 0, 2, "B"),
            ("role", 0, 3, "A"),
        ])
        director = ConversationAwareCalloutDirector(pt)
        director._build_callout_clip = lambda role: CalloutClip(
            path=Path("/tmp/fake.wav"), text="", role="_NARRATOR", clip_id=role, length_ms=0, offset_ms=0
        )
        assert director.calloutForBlock(BlockId(0, 1)) is not None
        assert director.calloutForBlock(BlockId(0, 2)) is not None
        assert director.calloutForBlock(BlockId(0, 3)) is None

    def test_direction_leading_role(self):
        segs = [DirectionSegment(segment_id=None, text="(_dir_)")]
        pt = build_play([("role", 0, 1, "A", segs)])
        director = ConversationAwareCalloutDirector(pt)
        director._build_callout_clip = lambda role: CalloutClip(
            path=Path("/tmp/fake.wav"), text="", role="_NARRATOR", clip_id=role, length_ms=0, offset_ms=0
        )
        clip = director.calloutForBlock(BlockId(0, 1))
        assert clip is not None

    def test_part_scoped_history(self):
        pt = build_play([
            ("role", 0, 0, "_NARRATOR"),
            ("role", 0, 1, "A"),
            ("role", 1, 0, "_NARRATOR"),
            ("role", 1, 1, "A"),
            ("role", 1, 2, "B"),
            ("role", 1, 3, "B"),
            ("role", 1, 4, "C"),
        ])
        director = ConversationAwareCalloutDirector(pt)
        director._build_callout_clip = lambda role: CalloutClip(
            path=Path("/tmp/fake.wav"), text="", role="_NARRATOR", clip_id=role, length_ms=0, offset_ms=0
        )
        assert director.calloutForBlock(BlockId(0, 1)).clip_id == 'A'
        assert director.calloutForBlock(BlockId(1, 1)).clip_id == 'A'
        assert director.calloutForBlock(BlockId(1, 2)).clip_id == 'B'
        assert director.calloutForBlock(BlockId(1, 3)) is None
        assert director.calloutForBlock(BlockId(1, 4)).clip_id == 'C'
