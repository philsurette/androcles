from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from stager.domain.block import BlockingBlock, DescriptionBlock, DirectionBlock, RoleBlock, TitleBlock
from stager.domain.block_id import BlockId
from stager.domain.play import Play, ReadingMetadata, SourceTextMetadata
from stager.domain.segment import BlockingSegment, DescriptionSegment, DirectionSegment, MetaSegment, SimultaneousSegment, SpeechSegment
from stager.domain.segment_id import SegmentId
from stager.linerecorder.recording_request_builder import RecordingRequestBuilder
from stager.production_publication.production_publisher import ProductionPublisher
from stager.production_publication.production_version_store import ProductionVersionStore
from stager.scriptwright import ProductionPlayLoader
from stager.shared import paths


def _cfg(tmp_path: Path) -> paths.PathConfig:
    return paths.PathConfig(
        play_name="test-play",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )


class _PublicationIds:
    def __init__(self, *ids: str) -> None:
        self.ids = list(ids)

    def generate(self) -> str:
        return self.ids.pop(0)


def _title_block() -> TitleBlock:
    block_id = BlockId(0, 0)
    return TitleBlock(
        block_id=block_id,
        text="## 0: Opening ##",
        segments=[MetaSegment(segment_id=SegmentId(block_id, 1), text="## 0: Opening ##", production_id="I-0:m1")],
        part_id=0,
        heading="Opening",
        production_id="I-0",
    )


def _speech_block(part_id: int | None, block_no: int, role: str, text: str) -> RoleBlock:
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
                production_id=f"I-{block_no}:s1",
            )
        ],
        production_id=f"I-{block_no}",
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
                production_id=f"I-{block_no}:s1",
            ),
            DirectionSegment(
                segment_id=SegmentId(block_id, 2),
                text="(_crossing_)",
                production_id=f"I-{block_no}:d1",
            ),
            SpeechSegment(
                segment_id=SegmentId(block_id, 3),
                text="I will follow.",
                role=role,
                production_id=f"I-{block_no}:s2",
            ),
        ],
        production_id=f"I-{block_no}",
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
                production_id=f"I-{block_no}:s1",
            )
        ],
        production_id=f"I-{block_no}",
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
                production_id=f"I-{block_no}:d1",
            )
        ],
        production_id=f"I-{block_no}",
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
                production_id=f"I-{block_no}:d1",
            )
        ],
        production_id=f"I-{block_no}",
    )


def _blocking_block(part_id: int, block_no: int, targets: list[str], text: str) -> BlockingBlock:
    block_id = BlockId(part_id, block_no)
    return BlockingBlock(
        block_id=block_id,
        text=text,
        targets=targets,
        segments=[
            BlockingSegment(
                segment_id=SegmentId(block_id, 1),
                text=text,
                targets=targets,
                production_id=f"I-{block_no}:b1",
            )
        ],
        production_id=f"I-{block_no}",
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
        build_id="build-123",
        build_timestamp="2026-05-10T14:00:00Z",
        created_at="2026-05-10T14:00:00Z",
    ).build()
    data = json.loads((cfg.build_dir / "linerecorder" / "MEGAERA" / "manifest.json").read_text(encoding="utf-8"))

    assert zip_path == cfg.build_dir / "linerecorder" / "MEGAERA.recording-request.zip"
    assert data["schema_version"] == 1
    assert data["format_version"] == "1.0.0"
    assert data["package_type"] == "recording_request"
    assert data["request"] == {
        "id": "test-play-MEGAERA-full_role-2026-05-10",
        "kind": "full_role",
        "created_at": "2026-05-10T14:00:00Z",
        "created_by": "stager",
    }
    assert data["play"]["title"] == "Androcles and the Lion"
    assert data["play"]["buildId"] == "build-123"
    assert data["play"]["buildTimestamp"] == "2026-05-10T14:00:00Z"
    assert data["production"] == {"source": "working"}
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
            "id": "I-2:s1",
            "line_id": "I-2",
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


def test_recording_request_builder_includes_cast_actor_metadata(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), response_block])
    cfg.play_dir.mkdir(parents=True, exist_ok=True)
    (cfg.play_dir / "cast.yaml").write_text(
        """
version: 1
actors:
  phil:
    display_name: Phil Surette
    email: phil@example.com
roles:
  MEGAERA:
    actor: phil
    recording: linerecorder
""",
        encoding="utf-8",
    )

    zip_path = RecordingRequestBuilder(
        play=play,
        paths=cfg,
        role="MEGAERA",
        created_at="2026-05-10T14:00:00Z",
    ).build()

    data = json.loads((cfg.build_dir / "linerecorder" / "MEGAERA" / "manifest.json").read_text(encoding="utf-8"))
    assert data["role"]["actor"] == {
        "id": "phil",
        "display_name": "Phil Surette",
        "email": "phil@example.com",
    }
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


def test_recording_request_builder_includes_blocking_context(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    blocking = _blocking_block(0, 2, ["MEGAERA"], "Cross to the milestone.")
    response_block = _inline_direction_block(0, 3, "MEGAERA")
    response_block.segments.insert(
        1,
        BlockingSegment(
            segment_id=SegmentId(response_block.block_id, 4),
            text="Take ANDROCLES' hand.",
            targets=["ANDROCLES"],
            production_id="I-3:b1",
        ),
    )
    next_block = _speech_block(0, 4, "MEGAERA", "I will go back.")
    play = _play([_title_block(), cue_block, blocking, response_block, next_block])

    data = RecordingRequestBuilder(
        play=play,
        paths=cfg,
        role="MEGAERA",
        created_at="2026-05-10T14:00:00Z",
    ).build_manifest().to_dict()

    assert data["items"][0]["blocking"] == [
        {
            "id": "I-3:b1",
            "targets": ["ANDROCLES"],
            "text": "Take ANDROCLES' hand.",
            "placement": "inline",
        },
        {
            "id": "I-2:b1",
            "targets": ["MEGAERA"],
            "text": "Cross to the milestone.",
            "placement": "before",
        },
    ]


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

    assert data["items"][0]["line_id"] == "I-1"
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
        selected_segment_ids={"I-2:s1"},
        created_at="2026-05-10T14:00:00Z",
    ).build_manifest().to_dict()

    assert data["request"]["kind"] == "selected_segments"
    assert [item["segment_id"] for item in data["items"]] == ["0_2_1"]
    assert data["items"][0]["reason"] == "selected_segments"


def test_recording_request_builder_can_set_selected_item_reason(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    first = _speech_block(0, 1, "MEGAERA", "I won't go another step.")
    second = _speech_block(0, 2, "MEGAERA", "I will go back.")
    play = _play([_title_block(), first, second])

    data = RecordingRequestBuilder(
        play=play,
        paths=cfg,
        role="MEGAERA",
        request_kind="selected_segments",
        selected_segment_ids={"I-2:s1"},
        item_reason="director_request",
        created_at="2026-05-10T14:00:00Z",
    ).build_manifest().to_dict()

    assert data["items"][0]["reason"] == "director_request"


def test_recording_request_builder_can_set_selected_item_reasons(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    first = _speech_block(0, 1, "MEGAERA", "I won't go another step.")
    second = _speech_block(0, 2, "MEGAERA", "I will go back.")
    play = _play([_title_block(), first, second])

    data = RecordingRequestBuilder(
        play=play,
        paths=cfg,
        role="MEGAERA",
        request_kind="production_update_v0002",
        selected_segment_ids={"I-1:s1", "I-2:s1"},
        selected_item_reasons={
            "I-1:s1": "script_changed",
            "I-2:s1": "script_added",
        },
        created_at="2026-05-10T14:00:00Z",
    ).build_manifest().to_dict()

    assert [item["reason"] for item in data["items"]] == ["script_changed", "script_added"]


def test_recording_request_builder_uses_synthetic_play_section_for_no_part_material(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    response_block = _speech_block(None, 1, "MEGAERA", "I won't go another step.")
    play = _play([response_block])

    data = RecordingRequestBuilder(
        play=play,
        paths=cfg,
        role="MEGAERA",
        created_at="2026-05-10T14:00:00Z",
    ).build_manifest().to_dict()

    assert data["items"][0]["section_id"] == "play"
    assert data["items"][0]["section_title"] == "Androcles and the Lion"
    assert data["items"][0]["scene_heading"] == "Androcles and the Lion"


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


def test_recording_request_builder_uses_production_ids_and_hashes(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cfg.production_markdown.parent.mkdir(parents=True, exist_ok=True)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
I-1 ANDROCLES: Well, dear, do you want to see one?
I-2 MEGAERA: I won't go another step.
""",
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()

    data = RecordingRequestBuilder(
        play=play,
        paths=cfg,
        role="MEGAERA",
        selected_segment_ids={"I-2:s1"},
        request_kind="selected_segments",
        created_at="2026-05-10T14:00:00Z",
    ).build_manifest().to_dict()

    item = data["items"][0]
    assert item["id"] == "I-2:s1"
    assert item["line_id"] == "I-2"
    assert item["segment_id"] == "1_2_1"
    assert item["line_content_hash"].startswith("sha256:")
    assert item["segment_content_hash"].startswith("sha256:")
    assert "production_id" not in json.dumps(data)


def test_recording_request_manifest_includes_published_production_metadata(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_lockable_production(cfg)
    ProductionPublisher(
        cfg,
        publication_id_generator=_PublicationIds("k9f4p2x8m1qd"),
        published_at_provider=lambda: "2026-05-10T13:00:00Z",
    ).publish(change_summary="Initial publish.")
    published_path = ProductionVersionStore(cfg).current_production_path()
    assert published_path is not None
    cfg.production_markdown = published_path
    play = ProductionPlayLoader(paths_config=cfg).load()

    data = RecordingRequestBuilder(
        play=play,
        paths=cfg,
        role="MEGAERA",
        created_at="2026-05-10T14:00:00Z",
    ).build_manifest().to_dict()

    assert data["request"]["production_version"] == "1@k9f4p2x8m1qd"
    assert data["play"]["version"] == "1@k9f4p2x8m1qd"
    assert data["production"] == {
        "source": "published",
        "version": "1@k9f4p2x8m1qd",
        "sequence": 1,
        "publication_id": "k9f4p2x8m1qd",
        "published_at": "2026-05-10T13:00:00Z",
    }


def test_recording_request_manifest_treats_legacy_history_as_working_source(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_lockable_production(cfg)
    legacy_current = cfg.build_dir / "production-history" / "current.json"
    legacy_current.parent.mkdir(parents=True)
    legacy_current.write_text(
        json.dumps({"version": 1, "label": "v0001", "published_at": "2026-05-13T18:31:49Z"}),
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()

    data = RecordingRequestBuilder(
        play=play,
        paths=cfg,
        role="MEGAERA",
        created_at="2026-05-10T14:00:00Z",
    ).build_manifest().to_dict()

    assert data["production"] == {"source": "working"}


def _write_lockable_production(cfg: paths.PathConfig) -> None:
    cfg.production_markdown.parent.mkdir(parents=True, exist_ok=True)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
I-1 ANDROCLES: Well, dear, do you want to see one?
I-2 MEGAERA: I won't go another step.
""",
        encoding="utf-8",
    )
