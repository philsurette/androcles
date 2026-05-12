from __future__ import annotations

import json
from pathlib import PurePosixPath

from stager.domain.block import DirectionBlock, RoleBlock
from stager.domain.block_id import BlockId
from stager.domain.play import Play, Reader, ReadingMetadata, SourceTextMetadata
from stager.domain.segment import DirectionSegment, SimultaneousSegment, SpeechSegment
from stager.domain.segment_id import SegmentId
from stager.playbook.app_audio_asset import AppAudioAsset
from stager.playbook.app_cue_start_offset import AppCueStartOffset
from stager.playbook.app_context_block import AppContextBlock
from stager.playbook.app_cue import AppCue
from stager.playbook.app_direction import AppDirection
from stager.playbook.app_line import AppLine
from stager.playbook.app_manifest import AppManifest
from stager.playbook.app_play import AppPlay
from stager.playbook.app_reading import AppReading
from stager.playbook.app_response import AppResponse
from stager.playbook.app_response_segment import AppResponseSegment
from stager.playbook.app_role import AppRole
from stager.playbook.app_section import AppSection


def _role_block(role: str = "MEGAERA") -> RoleBlock:
    block_id = BlockId(0, 5)
    return RoleBlock(
        block_id=block_id,
        role_names=[role],
        callout=role,
        text="I won't go another step.",
        segments=[
            SpeechSegment(
                segment_id=SegmentId(block_id, 1),
                role=role,
                text="I won't go another step.",
            )
        ],
    )


def test_manifest_serializes_schema_one_shape() -> None:
    block = _role_block()
    response_audio = AppAudioAsset(
        path=PurePosixPath("audio/segments/MEGAERA/0_5_1.wav"),
        duration_ms=2430,
    )
    cue_audio = AppAudioAsset(
        path=PurePosixPath("audio/segments/ANDROCLES/0_4_1.wav"),
        duration_ms=2100,
    )
    line = AppLine(
        id=AppLine.line_id_for(block, "MEGAERA"),
        part_id=0,
        block_id=AppLine.block_id_for(block),
        role="MEGAERA",
        speaker="MEGAERA",
        cue=AppCue(
            speaker="ANDROCLES",
            text="Well, dear, do you want to see one?",
            audio=cue_audio,
        ),
        response=AppResponse(
            text="I won't go another step.",
            segments=[
                AppResponseSegment(
                    id=str(block.segments[0].segment_id),
                    owners=["MEGAERA"],
                    text="I won't go another step.",
                    audio=response_audio,
                )
            ],
        ),
        previous_roles=["ANDROCLES"],
    )
    manifest = AppManifest(
        play=AppPlay(
            id="androcles",
            title="Androcles and the Lion",
            authors=["George Bernard Shaw"],
            source="Project Gutenberg",
        ),
        reading=AppReading(type="solo", build_type="custom"),
        sections=[
            AppSection(
                id="part-0",
                part_id=0,
                block_id="0.0",
                title="Opening",
                ordinal=0,
            )
        ],
        context=[
            AppContextBlock(
                id="0_0_1",
                part_id=0,
                block_id="0.0",
                kind="heading",
                speaker="_NARRATOR",
                text="Opening",
                audio=AppAudioAsset(
                    path=PurePosixPath("audio/segments/_NARRATOR/0_0_1.wav"),
                    duration_ms=1200,
                ),
            )
        ],
        roles=[
            AppRole(
                id="MEGAERA",
                display_name="MEGAERA",
                reader="Anonymous",
                parts=[0],
                lines=[line],
            )
        ],
    )

    data = json.loads(manifest.to_json())

    assert data["schema_version"] == 1
    assert data["play"]["id"] == "androcles"
    assert data["reading"] == {"type": "solo", "build_type": "custom"}
    assert data["sections"][0] == {
        "id": "part-0",
        "part_id": 0,
        "block_id": "0.0",
        "title": "Opening",
        "ordinal": 0,
    }
    assert data["context"][0]["kind"] == "heading"
    assert data["context"][0]["speaker"] == "_NARRATOR"
    assert data["roles"][0]["lines"][0]["id"] == "0_5_MEGAERA"
    assert data["roles"][0]["lines"][0]["block_id"] == "0.5"
    assert data["roles"][0]["lines"][0]["cue"]["audio"]["required"] is True
    assert data["roles"][0]["lines"][0]["response"]["segments"][0]["id"] == "0_5_1"


def test_solo_role_metadata_uses_default_reader() -> None:
    play = Play(
        reading_metadata=ReadingMetadata(
            reading_type="solo",
            readers=[Reader(id="_DEFAULT", reader="Phil")],
        ),
        blocks=[_role_block()],
    )

    role = AppRole.from_domain(play, play.getRole("MEGAERA"))

    assert role.display_name == "MEGAERA"
    assert role.reader == "Phil"
    assert role.parts == [0]


def test_audio_asset_serializes_cue_start_offsets() -> None:
    asset = AppAudioAsset(
        path=PurePosixPath("audio/segments/ANDROCLES/0_1_1.wav"),
        duration_ms=16000,
        cue_start_offsets=[
            AppCueStartOffset(
                requested_window_ms=10000,
                start_ms=5920,
                confidence="boundary",
            )
        ],
    )

    assert asset.to_dict() == {
        "path": "audio/segments/ANDROCLES/0_1_1.wav",
        "duration_ms": 16000,
        "required": True,
        "cue_start_offsets": [
            {
                "requested_window_ms": 10000,
                "start_ms": 5920,
                "confidence": "boundary",
            }
        ],
    }


def test_dramatic_role_metadata_uses_role_reader() -> None:
    play = Play(
        reading_metadata=ReadingMetadata(
            reading_type="dramatic",
            readers=[
                Reader(id="_DEFAULT", reader="Default Reader"),
                Reader(id="MEGAERA", reader="Jane Actor", role_name="Megæra"),
            ],
        ),
        blocks=[_role_block()],
    )

    role = AppRole.from_domain(play, play.getRole("MEGAERA"))

    assert role.display_name == "Megæra"
    assert role.reader == "Jane Actor"


def test_directions_preserve_inline_and_top_level_placement() -> None:
    block_id = BlockId(0, 7)
    inline_segment = DirectionSegment(
        segment_id=SegmentId(block_id, 2),
        text="(_suddenly throwing down her stick_)",
    )
    top_level_block_id = BlockId(0, 6)
    top_level_block = DirectionBlock(
        block_id=top_level_block_id,
        text="Androcles and Megæra come along the path.",
        segments=[
            DirectionSegment(
                segment_id=SegmentId(top_level_block_id, 1),
                text="Androcles and Megæra come along the path.",
            )
        ],
    )

    inline = AppDirection.from_segment(inline_segment, placement="inline")
    top_level = AppDirection.from_segment(top_level_block.segments[0], placement="top_level")

    assert inline.to_dict() == {
        "id": "0_7_2",
        "segment_id": "0_7_2",
        "text": "(_suddenly throwing down her stick_)",
        "placement": "inline",
    }
    assert top_level.to_dict()["segment_id"] == "0_6_1"
    assert top_level.to_dict()["placement"] == "top_level"


def test_simultaneous_response_segment_records_all_owners() -> None:
    block_id = BlockId(2, 73)
    segment = SimultaneousSegment(
        segment_id=SegmentId(block_id, 1),
        text="Hail, Caesar!",
        roles=["GLADIATOR-1", "GLADIATOR-2"],
    )
    response_segment = AppResponseSegment(
        id=str(segment.segment_id),
        owners=segment.roles,
        text=segment.text,
        audio=AppAudioAsset(
            path=PurePosixPath("audio/segments/GLADIATOR-1/2_73_1.wav"),
            duration_ms=1200,
        ),
        simultaneous=True,
    )

    data = response_segment.to_dict()

    assert data["id"] == "2_73_1"
    assert data["owners"] == ["GLADIATOR-1", "GLADIATOR-2"]
    assert data["simultaneous"] is True
