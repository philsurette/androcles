from __future__ import annotations

import json
import wave
import zipfile
from pathlib import Path
from pathlib import PurePosixPath

import pytest

from stager.domain.block import DescriptionBlock, DirectionBlock, RoleBlock, TitleBlock
from stager.domain.block_id import BlockId
from stager.domain.play import Play, ReadingMetadata, SourceTextMetadata
from stager.domain.segment import DescriptionSegment, DirectionSegment, MetaSegment, SpeechSegment
from stager.domain.segment_id import SegmentId
from stager.playbook.app_cue_start_offset import AppCueStartOffset
from stager.playbook.playbook_audio_packager import PackagedAudio
from stager.playbook.playbook_builder import PlaybookBuilder
from stager.audio.voice_profile_config import VoiceProfileConfigParser
from stager.audio.voice_profile_resolver import VoiceProfileResolver
from stager.audio.voice_render_cache import VoiceRenderCache
from stager.production_publication.production_publisher import ProductionPublisher
from stager.production_publication.production_version_store import ProductionVersionStore
from stager.scriptwright import ProductionPlayLoader
from stager.shared import paths
from stager.staging.diagram_state_builder import DiagramStateBuilder
from stager.staging.parser import StagingParser
from stager.staging.state_resolver import StagingStateResolver


def _write_wav(path: Path, duration_ms: int = 100) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_rate = 8_000
    frame_count = int(frame_rate * duration_ms / 1000)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(frame_rate)
        wav.writeframes(b"\x00\x00" * frame_count)


def _cfg(tmp_path: Path) -> paths.PathConfig:
    return paths.PathConfig(
        play_name="test-play",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )


def _named_cfg(tmp_path: Path, play_name: str) -> paths.PathConfig:
    return paths.PathConfig(
        play_name=play_name,
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


def _speech_block(part_id: int, block_no: int, role: str, text: str, callout: str | None = None) -> RoleBlock:
    block_id = BlockId(part_id, block_no)
    return RoleBlock(
        block_id=block_id,
        role_names=[role],
        callout=callout,
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


def _play(blocks) -> Play:
    return Play(
        source_text_metadata=SourceTextMetadata(
            title="Androcles and the Lion",
            authors=["George Bernard Shaw"],
            source="Project Gutenberg",
        ),
        reading_metadata=ReadingMetadata(reading_type="solo"),
        blocks=list(blocks),
    )


class _FakeCueStartOffsetAnalyzer:
    def analyze(self, audio_path: Path, duration_ms: int) -> list[AppCueStartOffset]:
        return [
            AppCueStartOffset(
                requested_window_ms=5000,
                start_ms=0,
                confidence="exact",
            )
        ]


class _FakeMp3Packager:
    def package(self, source_path: Path, destination_dir: Path) -> PackagedAudio:
        destination = destination_dir / source_path.with_suffix(".mp3").name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"fake mp3")
        return PackagedAudio(
            path=destination,
            manifest_path=PurePosixPath(
                destination.relative_to(destination_dir.parents[2]).as_posix()
            ),
        )


class _FakeProgressReporter:
    def __init__(self) -> None:
        self.started_total: int | None = None
        self.packaged: list[tuple[str, str, str]] = []
        self.finished = False

    def start_audio_packaging(self, total: int) -> None:
        self.started_total = total

    def audio_packaged(self, role: str, segment_id: str, category: str) -> None:
        self.packaged.append((role, segment_id, category))

    def finish_audio_packaging(self) -> None:
        self.finished = True


def _write_cleanup_review(cfg: paths.PathConfig, *, entries: list[tuple[str, str, Path]]) -> None:
    review_path = cfg.audio_out_dir / "cleaned" / "cleanup_review.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(
        json.dumps(
            {
                "play_id": cfg.play_name,
                "entries": [
                    {
                        "batch_id": "batch",
                        "role": role,
                        "segment_id": segment_id,
                        "output_path": output_path.as_posix(),
                        "warnings": [],
                        "fallback": False,
                    }
                    for role, segment_id, output_path in entries
                ],
            }
        ),
        encoding="utf-8",
    )


def _apply_delta(checkpoint: dict, delta: dict) -> dict:
    state = json.loads(json.dumps(checkpoint))
    for op in delta["targets"][0]["ops"]:
        if op["op"] == "upsert_entity":
            collection = "set_pieces" if op["entity"]["kind"] == "set_piece" else "entities"
            _upsert_by_id(state[collection], op["entity"])
        elif op["op"] == "remove_entity":
            state["entities"] = [entity for entity in state["entities"] if entity["id"] != op["id"]]
            state["set_pieces"] = [entity for entity in state["set_pieces"] if entity["id"] != op["id"]]
        elif op["op"] == "upsert_offstage":
            _upsert_by_id(state["offstage"], op["offstage"])
        elif op["op"] == "remove_offstage":
            state["offstage"] = [entity for entity in state["offstage"] if entity["id"] != op["id"]]
        elif op["op"] == "replace_diagnostics":
            state["diagnostics"] = op["diagnostics"]
    state["diagram_id"] = delta["targets"][0]["target_id"]
    state["diagram_kind"] = "beat"
    state["beat_id"] = delta["targets"][0]["beat_id"]
    return state


def _upsert_by_id(items: list[dict], item: dict) -> None:
    for index, candidate in enumerate(items):
        if candidate["id"] == item["id"]:
            items[index] = item
            return
    items.append(item)


def _write_voice_profiles(cfg: paths.PathConfig, *, roles: tuple[str, ...] = ("MEGAERA",)) -> None:
    cfg.play_dir.mkdir(parents=True, exist_ok=True)
    role_targets = "\n".join(
        f"""
  {role}:
    target:
      pitch_center_hz: 130
"""
        for role in roles
    )
    cast_profiles = "\n".join(
        f"""
  phil@{role}:
    actor: phil
    role: {role}
    mode: explicit
    transforms:
      - type: pitch
        semitones: 1.5
        strategy: preserve_tempo
"""
        for role in roles
    )
    (cfg.play_dir / "voice_profiles.yaml").write_text(
        f"""
version: 1
actors:
  phil:
    baseline:
      pitch_center_hz: 115
role_targets:
{role_targets}
cast_profiles:
{cast_profiles}
""",
        encoding="utf-8",
    )


def _rendered_voice_path(cfg: paths.PathConfig, *, role: str, segment_id: str) -> Path:
    config = VoiceProfileConfigParser().parse(cfg.play_dir / "voice_profiles.yaml")
    resolved = VoiceProfileResolver(config).resolve(role)
    assert resolved is not None
    cache = VoiceRenderCache(cfg)
    return cache.output_path(
        render_profile_id=cache.render_profile_id(resolved),
        role=role,
        segment_id=segment_id,
    )


def test_playbook_builder_writes_manifest_and_copies_required_audio(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), cue_block, response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_2_1.wav")

    zip_path = PlaybookBuilder(play=play, paths=cfg).build()
    manifest_path = cfg.build_dir / "app" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert zip_path == cfg.build_dir / "test-play.playbook.zip"
    assert zip_path.exists()
    megaera = next(role for role in data["roles"] if role["id"] == "MEGAERA")
    line = megaera["lines"][0]
    assert line["cue"]["speaker"] == "ANDROCLES"
    assert line["cue"]["audio"]["path"] == "audio/segments/ANDROCLES/0_1_1.wav"
    assert line["response"]["segments"][0]["audio"]["path"] == "audio/segments/MEGAERA/0_2_1.wav"
    assert (cfg.build_dir / "app" / line["cue"]["audio"]["path"]).exists()
    assert (cfg.build_dir / "app" / line["response"]["segments"][0]["audio"]["path"]).exists()
    assert data["sections"] == [
        {
            "id": "part-0",
            "part_id": 0,
            "block_id": "0.0",
            "title": "Opening",
            "ordinal": 0,
        }
    ]
    assert data["context"][0]["kind"] == "heading"
    assert data["context"][0]["speaker"] == "_NARRATOR"
    assert data["context"][0]["audio"]["path"] == "audio/segments/_NARRATOR/0_0_1.wav"
    with zipfile.ZipFile(zip_path) as archive:
        assert "manifest.json" in archive.namelist()
        assert line["cue"]["audio"]["path"] in archive.namelist()
        assert line["response"]["segments"][0]["audio"]["path"] in archive.namelist()


def test_playbook_builder_packages_blocking_diagram_bundle_when_staging_exists(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), cue_block, response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_2_1.wav")
    staging_path = cfg.build_dir / "staging" / "staging.txt"
    staging_path.parent.mkdir(parents=True)
    staging_text = """
stage type=proscenium
grid standard=9
actor AN name=Androcles
actor MG name=Megaera
setup act1
piece table kind=table at=C size=(5,3)

scene 1.1 set=act1
AN @ DL face=MG
MG @ UC
sword @ table

b1 @ I-2
MG move UC -> DR
sword remove
"""
    staging_path.write_text(staging_text, encoding="utf-8")

    zip_path = PlaybookBuilder(play=play, paths=cfg).build()
    manifest = json.loads((cfg.build_dir / "app" / "manifest.json").read_text(encoding="utf-8"))
    bundle_manifest_path = cfg.build_dir / "app" / manifest["staging"]["manifest_path"]
    bundle = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))
    checkpoint = json.loads((cfg.build_dir / "app" / bundle["checkpoints"][0]["path"]).read_text(encoding="utf-8"))
    delta = json.loads((cfg.build_dir / "app" / bundle["deltas"][0]["path"]).read_text(encoding="utf-8"))
    reconstructed = _apply_delta(checkpoint, delta)
    document = StagingParser().parse(staging_text)
    direct = DiagramStateBuilder().build(StagingStateResolver().resolve_beat(document, "1.1", "b1")).to_dict()

    assert manifest["format_version"] == "1.1.0"
    assert manifest["staging"] == {
        "included": True,
        "format": "quince.blocking.diagram_bundle",
        "format_version": "1.0.0",
        "manifest_path": "staging/diagram_manifest.json",
    }
    assert bundle["checkpoints"][0]["scene_id"] == "1.1"
    assert bundle["deltas"][0]["production_anchor"] == "I-2"
    assert delta["targets"][0]["ops"]
    assert any(entity["id"] == "actor:MG" and entity["source"] == "DR" for entity in reconstructed["entities"])
    assert delta["format"] == "quince.blocking.diagram_delta"
    assert reconstructed == direct
    with zipfile.ZipFile(zip_path) as archive:
        assert "staging/diagram_manifest.json" in archive.namelist()
        assert bundle["checkpoints"][0]["path"] in archive.namelist()
        assert bundle["deltas"][0]["path"] in archive.namelist()


def test_playbook_builder_omits_blocking_diagram_bundle_when_staging_does_not_exist(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), cue_block, response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_2_1.wav")

    PlaybookBuilder(play=play, paths=cfg).build()
    manifest = json.loads((cfg.build_dir / "app" / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["format_version"] == "1.0.0"
    assert "staging" not in manifest
    assert not (cfg.build_dir / "app" / "staging").exists()


def test_playbook_builder_can_exclude_blocking_diagram_bundle(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), cue_block, response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_2_1.wav")
    staging_path = cfg.build_dir / "staging" / "staging.txt"
    staging_path.parent.mkdir(parents=True)
    staging_path.write_text("stage type=proscenium\nscene 1.1\nAN @ DL\n", encoding="utf-8")

    PlaybookBuilder(play=play, paths=cfg, blocking_diagrams=False).build()
    manifest = json.loads((cfg.build_dir / "app" / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["format_version"] == "1.0.0"
    assert "staging" not in manifest
    assert not (cfg.build_dir / "app" / "staging").exists()


def test_playbook_builder_can_select_reviewed_cleaned_audio(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), cue_block, response_block])
    cleaned_narrator = cfg.audio_out_dir / "cleaned" / "batch" / "_NARRATOR" / "0_0_1.wav"
    cleaned_androcles = cfg.audio_out_dir / "cleaned" / "batch" / "ANDROCLES" / "0_1_1.wav"
    cleaned_megaera = cfg.audio_out_dir / "cleaned" / "batch" / "MEGAERA" / "0_2_1.wav"
    for path in (cleaned_narrator, cleaned_androcles, cleaned_megaera):
        _write_wav(path)
    _write_cleanup_review(
        cfg,
        entries=[
            ("_NARRATOR", "0_0_1", cleaned_narrator),
            ("ANDROCLES", "0_1_1", cleaned_androcles),
            ("MEGAERA", "0_2_1", cleaned_megaera),
        ],
    )

    work_items = PlaybookBuilder(play=play, paths=cfg).plan_audio_work()

    assert {item.source_path for item in work_items} == {
        cleaned_narrator,
        cleaned_androcles,
        cleaned_megaera,
    }


def test_playbook_builder_can_select_rendered_voice_profile_response_audio(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), cue_block, response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_2_1.wav")
    _write_voice_profiles(cfg, roles=("MEGAERA",))
    rendered_megaera = _rendered_voice_path(cfg, role="MEGAERA", segment_id="0_2_1")
    _write_wav(rendered_megaera)

    work_items = PlaybookBuilder(play=play, paths=cfg, voice_profiles=True).plan_audio_work()

    assert rendered_megaera in {item.source_path for item in work_items}
    assert cfg.segments_dir / "ANDROCLES" / "0_1_1.wav" in {item.source_path for item in work_items}


def test_playbook_builder_can_select_rendered_voice_profile_cue_audio(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), cue_block, response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_2_1.wav")
    _write_voice_profiles(cfg, roles=("ANDROCLES",))
    rendered_androcles = _rendered_voice_path(cfg, role="ANDROCLES", segment_id="0_1_1")
    _write_wav(rendered_androcles)

    work_items = PlaybookBuilder(play=play, paths=cfg, voice_profiles=True).plan_audio_work()

    assert rendered_androcles in {item.source_path for item in work_items}
    assert cfg.segments_dir / "MEGAERA" / "0_2_1.wav" in {item.source_path for item in work_items}


def test_playbook_builder_requires_rendered_voice_profile_audio_when_enabled(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), cue_block, response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_2_1.wav")
    _write_voice_profiles(cfg, roles=("MEGAERA",))

    with pytest.raises(RuntimeError, match="Voice-profile audio missing"):
        PlaybookBuilder(play=play, paths=cfg, voice_profiles=True).plan_audio_work()


def test_playbook_builder_fails_when_cleaned_audio_is_incomplete(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), cue_block, response_block])
    cleaned_narrator = cfg.audio_out_dir / "cleaned" / "batch" / "_NARRATOR" / "0_0_1.wav"
    _write_wav(cleaned_narrator)
    _write_cleanup_review(cfg, entries=[("_NARRATOR", "0_0_1", cleaned_narrator)])

    with pytest.raises(RuntimeError, match="no cleanup review output exists for ANDROCLES/0_1_1"):
        PlaybookBuilder(play=play, paths=cfg).plan_audio_work()


def test_playbook_builder_can_force_canonical_audio_when_cleanup_review_exists(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), cue_block, response_block])
    cleaned_narrator = cfg.audio_out_dir / "cleaned" / "batch" / "_NARRATOR" / "0_0_1.wav"
    _write_wav(cleaned_narrator)
    _write_cleanup_review(cfg, entries=[("_NARRATOR", "0_0_1", cleaned_narrator)])

    work_items = PlaybookBuilder(play=play, paths=cfg, audio_source="canonical").plan_audio_work()

    assert cfg.segments_dir / "_NARRATOR" / "0_0_1.wav" in {item.source_path for item in work_items}


def test_playbook_builder_includes_callout_audio_when_present(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.", callout="ANDROCLES")
    play = _play([_title_block(), cue_block, response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_2_1.wav")
    _write_wav(cfg.build_dir / "audio" / "callouts" / "ANDROCLES.wav")

    PlaybookBuilder(play=play, paths=cfg).build()
    manifest_path = cfg.build_dir / "app" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    megaera = next(role for role in data["roles"] if role["id"] == "MEGAERA")
    line = megaera["lines"][0]
    assert line["speaker"] == "ANDROCLES"
    assert not line.get("callout")
    assert any(asset["path"] == "audio/callouts/ANDROCLES/ANDROCLES.wav" for asset in data["assets"])

    with zipfile.ZipFile(cfg.build_dir / "test-play.playbook.zip") as archive:
        assert "audio/callouts/ANDROCLES/ANDROCLES.wav" in archive.namelist()


def test_playbook_builder_uses_alternate_callout_audio_location(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.", callout="CHRISTIAN-1")
    play = _play([_title_block(), cue_block, response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_2_1.wav")
    _write_wav(cfg.build_dir / "audio" / "callouts" / "CHRISTIAN.wav")

    PlaybookBuilder(play=play, paths=cfg).build()

    manifest_path = cfg.build_dir / "app" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert any(asset["path"] == "audio/callouts/CHRISTIAN-1/CHRISTIAN.wav" for asset in data["assets"])

    with zipfile.ZipFile(cfg.build_dir / "test-play.playbook.zip") as archive:
        assert "audio/callouts/CHRISTIAN-1/CHRISTIAN.wav" in archive.namelist()


def test_playbook_builder_plans_context_cue_and_response_audio(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    title_block = _title_block()
    description_block = _description_block(0, 1, "A path through a forest.")
    direction_block = _direction_block(0, 2, "Androcles enters.")
    response_block = _speech_block(0, 3, "MEGAERA", "I won't go another step.")
    play = _play([title_block, description_block, direction_block, response_block])

    work_items = PlaybookBuilder(play=play, paths=cfg).plan_audio_work()

    assert [(item.role, item.segment_id, item.category) for item in work_items] == [
        ("_NARRATOR", "0_2_1", "cue"),
        ("MEGAERA", "0_3_1", "response"),
        ("_NARRATOR", "0_0_1", "context"),
        ("_NARRATOR", "0_1_1", "context"),
        ("_NARRATOR", "0_2_1", "context"),
    ]


def test_playbook_builder_reports_audio_packaging_progress(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    title_block = _title_block()
    description_block = _description_block(0, 1, "A path through a forest.")
    direction_block = _direction_block(0, 2, "Androcles enters.")
    response_block = _speech_block(0, 3, "MEGAERA", "I won't go another step.")
    play = _play([title_block, description_block, direction_block, response_block])
    for segment_id in ("0_0_1", "0_1_1", "0_2_1"):
        _write_wav(cfg.segments_dir / "_NARRATOR" / f"{segment_id}.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_3_1.wav")
    reporter = _FakeProgressReporter()

    PlaybookBuilder(play=play, paths=cfg, progress_reporter=reporter).build()

    assert reporter.started_total == 5
    assert reporter.packaged == [
        ("_NARRATOR", "0_2_1", "cue"),
        ("MEGAERA", "0_3_1", "response"),
        ("_NARRATOR", "0_0_1", "context"),
        ("_NARRATOR", "0_1_1", "context"),
        ("_NARRATOR", "0_2_1", "context"),
    ]
    assert reporter.finished is True


def test_playbook_builder_reports_mp3_packaging_progress(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    response_block = _speech_block(0, 1, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav")
    reporter = _FakeProgressReporter()

    PlaybookBuilder(
        play=play,
        paths=cfg,
        audio_format="mp3",
        audio_packager=_FakeMp3Packager(),
        progress_reporter=reporter,
    ).build()

    assert reporter.started_total == 3
    assert reporter.packaged == [
        ("_NARRATOR", "0_0_1", "cue"),
        ("MEGAERA", "0_1_1", "response"),
        ("_NARRATOR", "0_0_1", "context"),
    ]
    assert reporter.finished is True


def test_playbook_builder_plans_inline_directions(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    role_block = RoleBlock(
        block_id=BlockId(0, 2),
        role_names=["MEGAERA"],
        callout="MEGAERA",
        text="((Stage note)) I won't go another step.",
        segments=[
            DirectionSegment(
                segment_id=SegmentId(BlockId(0, 2), 1),
                text="(stage note)",
                production_id="I-2:d1",
            ),
            SpeechSegment(
                segment_id=SegmentId(BlockId(0, 2), 2),
                text="I won't go another step.",
                role="MEGAERA",
                production_id="I-2:s1",
            ),
        ],
        production_id="I-2",
    )
    play = _play([_title_block(), cue_block, role_block])
    for segment_id in ("0_0_1", "0_1_1", "0_2_1", "0_2_2"):
        _write_wav(cfg.segments_dir / "_NARRATOR" / f"{segment_id}.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_2_2.wav")
    _write_wav(cfg.build_dir / "audio" / "callouts" / "MEGAERA.wav")

    work_items = PlaybookBuilder(play=play, paths=cfg).plan_audio_work()
    assert ("_NARRATOR", "0_2_1", "direction") in [(item.role, item.segment_id, item.category) for item in work_items]

    zip_path = PlaybookBuilder(play=play, paths=cfg).build()
    manifest_path = cfg.build_dir / "app" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert zip_path.exists()
    assert "audio/segments/_NARRATOR/0_2_1.wav" in {
        entry["path"] for entry in manifest["assets"]
    }
    with zipfile.ZipFile(zip_path) as archive:
        assert "audio/segments/_NARRATOR/0_2_1.wav" in archive.namelist()


def test_playbook_builder_attaches_offsets_to_cue_audio_only(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), cue_block, response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_2_1.wav")

    PlaybookBuilder(
        play=play,
        paths=cfg,
        cue_start_offset_analyzer=_FakeCueStartOffsetAnalyzer(),
    ).build()
    data = json.loads((cfg.build_dir / "app" / "manifest.json").read_text(encoding="utf-8"))

    line = next(role for role in data["roles"] if role["id"] == "MEGAERA")["lines"][0]
    assert line["cue"]["audio"]["cue_start_offsets"] == [
        {
            "requested_window_ms": 5000,
            "start_ms": 0,
            "confidence": "exact",
        }
    ]
    assert "cue_start_offsets" not in line["response"]["segments"][0]["audio"]


def test_playbook_builder_can_package_audio_as_mp3_with_wav_derived_offsets(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), cue_block, response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_2_1.wav")

    zip_path = PlaybookBuilder(
        play=play,
        paths=cfg,
        audio_format="mp3",
        cue_start_offset_analyzer=_FakeCueStartOffsetAnalyzer(),
        audio_packager=_FakeMp3Packager(),
    ).build()
    data = json.loads((cfg.build_dir / "app" / "manifest.json").read_text(encoding="utf-8"))

    line = next(role for role in data["roles"] if role["id"] == "MEGAERA")["lines"][0]
    assert line["cue"]["audio"]["path"] == "audio/segments/ANDROCLES/0_1_1.mp3"
    assert line["cue"]["audio"]["cue_start_offsets"] == [
        {
            "requested_window_ms": 5000,
            "start_ms": 0,
            "confidence": "exact",
        }
    ]
    assert line["response"]["segments"][0]["audio"]["path"] == "audio/segments/MEGAERA/0_2_1.mp3"
    with zipfile.ZipFile(zip_path) as archive:
        assert "audio/segments/ANDROCLES/0_1_1.mp3" in archive.namelist()
        assert "audio/segments/MEGAERA/0_2_1.mp3" in archive.namelist()


def test_playbook_builder_exports_narrator_context_blocks(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    title_block = _title_block()
    description_block = _description_block(0, 1, "A path through a forest.")
    direction_block = _direction_block(0, 2, "Androcles enters.")
    response_block = _speech_block(0, 3, "MEGAERA", "I won't go another step.")
    play = _play([title_block, description_block, direction_block, response_block])
    for segment_id in ("0_0_1", "0_1_1", "0_2_1"):
        _write_wav(cfg.segments_dir / "_NARRATOR" / f"{segment_id}.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_3_1.wav")

    PlaybookBuilder(play=play, paths=cfg).build()
    manifest_path = cfg.build_dir / "app" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert [block["kind"] for block in data["context"]] == ["heading", "description", "direction"]
    assert [block["text"] for block in data["context"]] == [
        "Opening",
        "A path through a forest.",
        "Androcles enters.",
    ]
    assert data["context"][1]["audio"]["path"] == "audio/segments/_NARRATOR/0_1_1.wav"
    assert data["context"][2]["audio"]["path"] == "audio/segments/_NARRATOR/0_2_1.wav"
    assert "_ANNOUNCER" not in {block["speaker"] for block in data["context"]}


def test_playbook_builder_uses_part_title_as_first_line_cue(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    response_block = _speech_block(0, 1, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav")

    PlaybookBuilder(play=play, paths=cfg).build()
    manifest_path = cfg.build_dir / "app" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    line = data["roles"][0]["lines"][0]
    assert line["cue"]["speaker"] == "_NARRATOR"
    assert line["cue"]["text"] == "Opening"
    assert line["cue"]["audio"]["path"] == "audio/segments/_NARRATOR/0_0_1.wav"


def test_playbook_builder_fails_on_missing_response_audio(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cue_block = _speech_block(0, 1, "ANDROCLES", "Well, dear, do you want to see one?")
    response_block = _speech_block(0, 2, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), cue_block, response_block])
    _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")

    with pytest.raises(RuntimeError, match="Missing required response audio for role MEGAERA segment 0_2_1"):
        PlaybookBuilder(play=play, paths=cfg).build()


def test_playbook_builder_fails_on_missing_cue_audio(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    response_block = _speech_block(0, 1, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), response_block])
    _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav")

    with pytest.raises(RuntimeError, match="Missing required cue audio for role _NARRATOR segment 0_0_1"):
        PlaybookBuilder(play=play, paths=cfg).build()


def test_playbook_builder_keeps_path_configs_isolated(tmp_path: Path) -> None:
    first_cfg = _named_cfg(tmp_path, "first-play")
    second_cfg = _named_cfg(tmp_path, "second-play")
    response_block = _speech_block(0, 1, "MEGAERA", "I won't go another step.")
    play = _play([_title_block(), response_block])
    for cfg in (first_cfg, second_cfg):
        _write_wav(cfg.segments_dir / "_NARRATOR" / "0_0_1.wav")
        _write_wav(cfg.segments_dir / "MEGAERA" / "0_1_1.wav")

    first_zip = PlaybookBuilder(play=play, paths=first_cfg).build()
    second_zip = PlaybookBuilder(play=play, paths=second_cfg).build()

    assert first_zip == first_cfg.build_dir / "first-play.playbook.zip"
    assert second_zip == second_cfg.build_dir / "second-play.playbook.zip"
    assert first_zip.exists()
    assert second_zip.exists()
    assert (first_cfg.build_dir / "app" / "manifest.json").exists()
    assert (second_cfg.build_dir / "app" / "manifest.json").exists()


def test_playbook_manifest_uses_production_ids_and_hashes(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cfg.production_markdown.parent.mkdir(parents=True, exist_ok=True)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
I-1 ANDROCLES: Well, dear, do you want to see one?
I-2 MEGAERA: (_suddenly_) I won't go another step.
""",
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()
    _write_wav(cfg.segments_dir / "_NARRATOR" / "1_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "1_1_1.wav")
    _write_wav(cfg.segments_dir / "_NARRATOR" / "1_2_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "1_2_2.wav")

    PlaybookBuilder(play=play, paths=cfg).build()
    data = json.loads((cfg.build_dir / "app" / "manifest.json").read_text(encoding="utf-8"))

    megaera = next(role for role in data["roles"] if role["id"] == "MEGAERA")
    line = megaera["lines"][0]
    assert line["id"] == "I-2"
    assert line["content_hash"].startswith("sha256:")
    assert line["block_id"] == "1.2"
    assert line["response"]["segments"][0]["id"] == "I-2:s1"
    assert line["response"]["segments"][0]["segment_id"] == "1_2_2"
    assert line["response"]["segments"][0]["content_hash"].startswith("sha256:")
    assert line["directions"][0]["id"] == "I-2:d1"
    assert line["directions"][0]["segment_id"] == "1_2_1"
    assert line["directions"][0]["content_hash"].startswith("sha256:")
    assert "production_id" not in json.dumps(data)


def test_playbook_manifest_includes_published_production_metadata(tmp_path: Path) -> None:
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
    _write_production_playbook_audio(cfg)

    PlaybookBuilder(play=play, paths=cfg).build()
    data = json.loads((cfg.build_dir / "app" / "manifest.json").read_text(encoding="utf-8"))

    assert data["production"] == {
        "source": "published",
        "version": "1@k9f4p2x8m1qd",
        "sequence": 1,
        "publication_id": "k9f4p2x8m1qd",
        "published_at": "2026-05-10T13:00:00Z",
        "change_summary": "Initial publish.",
    }


def test_playbook_manifest_includes_published_blocking_changes(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cfg.production_markdown.parent.mkdir(parents=True, exist_ok=True)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
I-1 ANDROCLES: Well, dear, do you want to see one?
/ANDROCLES: Cross left.
I-2 MEGAERA: I won't go another step.
""",
        encoding="utf-8",
    )
    ProductionPublisher(
        cfg,
        publication_id_generator=_PublicationIds("k9f4p2x8m1qd"),
        published_at_provider=lambda: "2026-05-10T13:00:00Z",
    ).publish(change_summary="Initial publish.")
    cfg.production_markdown.write_text(
        cfg.production_markdown.read_text(encoding="utf-8").replace("Cross left", "Cross right"),
        encoding="utf-8",
    )
    ProductionPublisher(
        cfg,
        publication_id_generator=_PublicationIds("z8n3d5q1w6te"),
        published_at_provider=lambda: "2026-05-11T13:00:00Z",
    ).publish(change_summary="Updated blocking.")
    published_path = ProductionVersionStore(cfg).current_production_path()
    assert published_path is not None
    cfg.production_markdown = published_path
    play = ProductionPlayLoader(paths_config=cfg).load()
    _write_production_playbook_audio(cfg)

    PlaybookBuilder(play=play, paths=cfg).build()
    data = json.loads((cfg.build_dir / "app" / "manifest.json").read_text(encoding="utf-8"))

    assert data["production"]["change_summary"] == "Updated blocking."
    assert data["production"]["blocking_changes"] == ["I-2:b1"]


def test_playbook_manifest_marks_working_source_production_metadata(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_lockable_production(cfg)
    ProductionPublisher(
        cfg,
        publication_id_generator=_PublicationIds("k9f4p2x8m1qd"),
        published_at_provider=lambda: "2026-05-10T13:00:00Z",
    ).publish(change_summary="Initial publish.")
    before = cfg.production_markdown.read_text(encoding="utf-8")
    play = ProductionPlayLoader(paths_config=cfg).load()
    _write_production_playbook_audio(cfg)

    PlaybookBuilder(play=play, paths=cfg).build()
    data = json.loads((cfg.build_dir / "app" / "manifest.json").read_text(encoding="utf-8"))

    assert data["production"] == {
        "source": "working",
        "version": "1@k9f4p2x8m1qd",
        "sequence": 1,
        "publication_id": "k9f4p2x8m1qd",
    }
    assert cfg.production_markdown.read_text(encoding="utf-8") == before


def test_playbook_manifest_treats_legacy_history_as_working_source(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    _write_lockable_production(cfg)
    legacy_current = cfg.build_dir / "production-history" / "current.json"
    legacy_current.parent.mkdir(parents=True)
    legacy_current.write_text(
        json.dumps({"version": 1, "label": "v0001", "published_at": "2026-05-13T18:31:49Z"}),
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()
    _write_production_playbook_audio(cfg)

    PlaybookBuilder(play=play, paths=cfg).build()
    data = json.loads((cfg.build_dir / "app" / "manifest.json").read_text(encoding="utf-8"))

    assert data["production"] == {"source": "working"}


def test_playbook_manifest_exports_blocking_without_required_audio(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    cfg.production_markdown.parent.mkdir(parents=True, exist_ok=True)
    cfg.production_markdown.write_text(
        """// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
I-1 ANDROCLES: Hello (_/MEGAERA: crosses behind ANDROCLES_) there.
/MEGAERA: Moves upstage.
""",
        encoding="utf-8",
    )
    play = ProductionPlayLoader(paths_config=cfg).load()
    _write_wav(cfg.segments_dir / "_NARRATOR" / "1_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "1_1_1.wav")

    PlaybookBuilder(play=play, paths=cfg).build()
    data = json.loads((cfg.build_dir / "app" / "manifest.json").read_text(encoding="utf-8"))

    androcles = next(role for role in data["roles"] if role["id"] == "ANDROCLES")
    line = androcles["lines"][0]
    assert line["blocking"] == [
        {
            "id": "I-1:b1",
            "targets": ["MEGAERA"],
            "text": "crosses behind ANDROCLES",
            "placement": "inline",
            "segment_id": "1_1_2",
            "content_hash": line["blocking"][0]["content_hash"],
        }
    ]
    assert line["blocking"][0]["content_hash"].startswith("sha256:")
    blocking_context = next(block for block in data["context"] if block["kind"] == "blocking")
    assert blocking_context["id"] == "I-1:b2"
    assert blocking_context["targets"] == ["MEGAERA"]
    assert blocking_context["placement"] == "after"
    assert blocking_context["text"] == "Moves upstage."
    assert "audio" not in blocking_context


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


def _write_production_playbook_audio(cfg: paths.PathConfig) -> None:
    _write_wav(cfg.segments_dir / "_NARRATOR" / "1_0_1.wav")
    _write_wav(cfg.segments_dir / "ANDROCLES" / "1_1_1.wav")
    _write_wav(cfg.segments_dir / "MEGAERA" / "1_2_1.wav")
