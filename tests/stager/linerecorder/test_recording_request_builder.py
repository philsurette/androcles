from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from stager.domain.block import DescriptionBlock, DirectionBlock, RoleBlock, TitleBlock
from stager.domain.block_id import BlockId
from stager.domain.play import Play, ReadingMetadata, SourceTextMetadata
from stager.domain.segment import DescriptionSegment, DirectionSegment, MetaSegment, SimultaneousSegment, SpeechSegment
from stager.domain.segment_id import SegmentId
from stager.linerecorder.recording_request_builder import RecordingRequestBuilder
from stager.shared import paths


def _cfg(tmp_path: Path) -> paths.PathConfig:
    return paths.PathConfig(
        play_name="test-play",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )


def _title_block() -> TitleBlock:
    block_id = BlockId(0, 0)
    return TitleBlock(
        block_id=block_id,
        text="## 0: Opening ##",
        segments=[MetaSegment(segment_id=SegmentId(block_id, 1), text="## 0: Opening ##")],
        part_id=0,
        heading="Opening",
    )


def _speech_block(part_id: int, block_no: int, role: str, text: str) -> RoleBlock:
    block_id = BlockId(part_id, block_no)
    return RoleBlock(
        block_id=block_id,
        role_names=[role],
        callout=role,
        text=text,
        segments=[
            SpeechSegment(
                segment_id=SegmentId(block_id, 1),
                text=text,
                role=role,
            )
        ],
    )


def _inline_direction_block(part_id: int, block_no: int, role: str) -> RoleBlock:
    block_id = BlockId(part_id, block_no)
    return RoleBlock(
        block_id=block_id,
        role_names=[role],
        callout=role,
        text="Go on. (_crossing_) I will follow.",
        segments=[
            SpeechSegment(
                segment_id=SegmentId(block_id, 1),
                text="Go on.",
                role=role,
            ),
            DirectionSegment(
                segment_id=SegmentId(block_id, 2),
                text="(_crossing_)",
            ),
            SpeechSegment(
                segment_id=SegmentId(block_id, 3),
                text="I will follow.",
                role=role,
            ),
        ],
    )


def _simultaneous_block(part_id: int, block_no: int, roles: list[str], text: str) -> RoleBlock:
    block_id = BlockId(part_id, block_no)
    return RoleBlock(
        block_id=block_id,
        role_names=roles,
        callout="SOLDIERS",
        text=text,
        segments=[
            SimultaneousSegment(
                segment_id=SegmentId(block_id, 1),
                text=text,
                roles=roles,
            )
        ],
    )


def _description_block(part_id: int, block_no: int, text: str) -> DescriptionBlock:
    block_id = BlockId(part_id, block_no)
    return DescriptionBlock(
        block_id=block_id,
        text=text,
        segments=[
            DescriptionSegment(
                segment_id=SegmentId(block_id, 1),
                text=text,
            )
        ],
    )


def _direction_block(part_id: int, block_no: int, text: str) -> DirectionBlock:
    block_id = BlockId(part_id, block_no)
    return DirectionBlock(
        block_id=block_id,
        text=text,
        segments=[
            DirectionSegment(
                segment_id=SegmentId(block_id, 1),
                text=text,
            )
        ],
    )


def _play(blocks) -> Play:
    return Play(
        source_text_metadata=SourceTextMetadata(
            title="Androcles and the Lion",
            authors=["George Bernard Shaw"],
        ),
        reading_metadata=ReadingMetadata(reading_type="dramatic"),
        blocks=list(blocks),
    )


def test_recording_request_builder_writes_full_role_request(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    next_block = _speech_block(0, 3, "ANDROCLES", "Then stay here.")
    play = _play([_title_block(), cue_block, response_block, next_block])

    zip_path = RecordingRequestBuilder(
        play=play,
        paths=cfg,
        role="MEGAERA",
        created_at="2026-05-10T14:00:00Z",
    ).build()
    data = json.loads((cfg.build_dir / "linerecorder" / "MEGAERA" / "manifest.json").read_text(encoding="utf-8"))

    assert zip_path == cfg.build_dir / "linerecorder" / "MEGAERA.recording-request.zip"
    assert data["package_type"] == "recording_request"
    assert data["request"] == {
        "id": "test-play-MEGAERA-full_role-2026-05-10",
        "kind": "full_role",
        "created_at": "2026-05-10T14:00:00Z",
        "created_by": "stager",
    }
    assert data["play"]["title"] == "Androcles and the Lion"
    assert data["role"] == {
        "id": "MEGAERA",
        "display_name": "MEGAERA",
    }
    assert data["recording"] == {
        "preferred_sample_rate_hz": 48000,
        "preferred_channels": 1,
        "source_format": "wav",
    }
    assert data["items"] == [
        {
            "line_id": "0_2_MEGAERA",
            "block_id": "0.2",
            "segment_id": "0_2_1",
            "sequence": 1,
            "display_text": "I won't go another step.",
            "segment_text": "I won't go another step.",
            "output_path": "audio/segments/MEGAERA/0_2_1.wav",
            "cue_text": "Well, dear, do you want to see one?",
            "cue_speaker": "ANDROCLES",
            "next_text": "Then stay here.",
            "next_speaker": "ANDROCLES",
            "section_id": "part-0",
            "section_title": "Opening",
            "scene_heading": "Opening",
            "reason": "initial_recording",
        }
    ]
    with zipfile.ZipFile(zip_path) as archive:
        assert archive.namelist() == ["manifest.json"]


def test_recording_request_builder_includes_inline_directions_and_multiple_segments(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _description_block(0, 1, "A clearing in the forest.")
    response_block = _inline_direction_block(0, 2, "MEGAERA")
    play = _play([_title_block(), cue_block, response_block])

    manifest = RecordingRequestBuilder(
        play=play,
        paths=cfg,
        role="MEGAERA",
        created_at="2026-05-10T14:00:00Z",
    ).build_manifest()
    data = manifest.to_dict()

    assert [item["segment_id"] for item in data["items"]] == ["0_2_1", "0_2_3"]
    assert [item["sequence"] for item in data["items"]] == [1, 2]
    assert data["items"][0]["display_text"] == "Go on. (_crossing_) I will follow."
    assert data["items"][0]["segment_text"] == "Go on."
    assert data["items"][1]["segment_text"] == "I will follow."
    assert data["items"][0]["stage_directions"] == ["(_crossing_)"]
    assert data["items"][0]["cue_text"] == "A clearing in the forest."
    assert data["items"][0]["cue_speaker"] == "_NARRATOR"
    assert "previous_text" not in data["items"][0]


def test_recording_request_builder_marks_simultaneous_segments(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    response_block = _simultaneous_block(0, 1, ["CENTURION", "SOLDIER"], "Halt!")
    play = _play([_title_block(), response_block])

    data = RecordingRequestBuilder(
        play=play,
        paths=cfg,
        role="CENTURION",
        created_at="2026-05-10T14:00:00Z",
    ).build_manifest().to_dict()

    assert data["items"][0]["line_id"] == "0_1_CENTURION"
    assert data["items"][0]["segment_id"] == "0_1_1"
    assert data["items"][0]["simultaneous"] is True
    assert data["items"][0]["cue_text"] == "Opening"


def test_recording_request_builder_can_emit_selected_segments(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    first = _speech_block(0, 1, "MEGAERA", "I won't go another step.")
    second = _speech_block(0, 2, "MEGAERA", "I will go back.")
    play = _play([_title_block(), first, second])

    data = RecordingRequestBuilder(
        play=play,
        paths=cfg,
        role="MEGAERA",
        request_kind="selected_segments",
        selected_segment_ids={"0_2_1"},
        created_at="2026-05-10T14:00:00Z",
    ).build_manifest().to_dict()

    assert data["request"]["kind"] == "selected_segments"
    assert [item["segment_id"] for item in data["items"]] == ["0_2_1"]
    assert data["items"][0]["reason"] == "selected_segments"


def test_recording_request_builder_rejects_unknown_selected_segments(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    play = _play([_title_block(), _speech_block(0, 1, "MEGAERA", "I won't go another step.")])

    with pytest.raises(ValueError, match="Selected segment ids do not belong to role MEGAERA: 0_99_1"):
        RecordingRequestBuilder(
            play=play,
            paths=cfg,
            role="MEGAERA",
            request_kind="selected_segments",
            selected_segment_ids={"0_99_1"},
            created_at="2026-05-10T14:00:00Z",
        ).build_manifest()


def test_recording_request_builder_rejects_meta_roles(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    play = _play([_title_block(), _direction_block(0, 1, "Androcles enters.")])

    with pytest.raises(ValueError, match="Unknown rehearsable role: _NARRATOR"):
        RecordingRequestBuilder(
            play=play,
            paths=cfg,
            role="_NARRATOR",
        ).build_manifest()
