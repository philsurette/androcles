from __future__ import annotations

import io
import json
from pathlib import Path
import wave
import zipfile

import pytest

from stager.domain.block import RoleBlock
from stager.domain.block_id import BlockId
from stager.domain.play import Play
from stager.domain.segment import SpeechSegment
from stager.domain.segment_id import SegmentId
from stager.linerecorder.role_recordings_importer import RecordingImportProcessingOptions, RoleRecordingsImporter
from stager.playbook.playbook_builder import PlaybookBuilder
from stager.scriptwright.production_play_loader import ProductionPlayLoader
from stager.shared import paths


def _cfg(tmp_path: Path) -> paths.PathConfig:
    return paths.PathConfig(
        play_name="androcles",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )


def test_role_recordings_importer_writes_segments_to_stager_tree(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    package_path = tmp_path / "CENTURION.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": False,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "recordings": [
                {
                    "id": "I-12:s1",
                    "line_id": "I-12",
                    "block_id": "0.12",
                    "segment_id": "0_12_1",
                    "audio_path": "audio/segments/CENTURION/0_12_1.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": ["I-14:s1"],
        },
        files={"audio/segments/CENTURION/0_12_1.wav": _wav_bytes()},
    )

    result = RoleRecordingsImporter(paths=cfg).import_package(package_path)

    assert result.role == "CENTURION"
    assert result.imported_count == 1
    assert result.complete is False
    assert result.missing_segment_ids == ["I-14:s1"]
    assert (cfg.segments_dir / "CENTURION" / "0_12_1.wav").read_bytes() == _wav_bytes()


def test_role_recordings_importer_records_existing_segment_before_overwrite(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    existing_path = cfg.segments_dir / "CENTURION" / "0_12_1.wav"
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    existing_path.write_bytes(b"existing wav")
    package_path = tmp_path / "CENTURION.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "recordings": [
                {
                    "id": "I-12:s1",
                    "line_id": "I-12",
                    "block_id": "0.12",
                    "segment_id": "0_12_1",
                    "audio_path": "audio/segments/CENTURION/0_12_1.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={"audio/segments/CENTURION/0_12_1.wav": _wav_bytes(b"\x02\x00")},
    )

    result = RoleRecordingsImporter(paths=cfg).import_package(package_path)

    assert existing_path.read_bytes() == _wav_bytes(b"\x02\x00")
    transaction = json.loads(result.transaction_manifest_path.read_text(encoding="utf-8"))
    assert transaction["source_package"] == package_path.as_posix()
    assert transaction["imported"][0]["segment_id"] == "0_12_1"
    assert transaction["imported"][0]["existed_before"] is True
    backup_path = result.transaction_manifest_path.parent / "backups" / "audio" / "segments" / "CENTURION" / "0_12_1.wav"
    incoming_path = result.transaction_manifest_path.parent / "incoming" / "audio" / "segments" / "CENTURION" / "0_12_1.wav"
    assert backup_path.read_bytes() == b"existing wav"
    assert incoming_path.read_bytes() == _wav_bytes(b"\x02\x00")


def test_role_recordings_importer_records_new_segment_without_backup(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    package_path = tmp_path / "CENTURION.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "recordings": [
                {
                    "id": "I-12:s1",
                    "line_id": "I-12",
                    "block_id": "0.12",
                    "segment_id": "0_12_1",
                    "audio_path": "audio/segments/CENTURION/0_12_1.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={"audio/segments/CENTURION/0_12_1.wav": _wav_bytes()},
    )

    result = RoleRecordingsImporter(paths=cfg).import_package(package_path)

    transaction = json.loads(result.transaction_manifest_path.read_text(encoding="utf-8"))
    assert transaction["imported"][0]["existed_before"] is False
    assert "backup_path" not in transaction["imported"][0]
    assert not (result.transaction_manifest_path.parent / "backups").exists()


def test_role_recordings_importer_processes_recordings_with_floor_noise(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    package_path = tmp_path / "CENTURION.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "floor_noise_recordings": [
                {
                    "id": "floor-20260511T115900Z",
                    "audio_path": "noise/floor-20260511T115900Z.wav",
                    "recorded_at": "2026-05-11T11:59:00Z",
                    "duration_ms": 5000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "device_label": "USB Microphone",
                    "mode": "clean",
                }
            ],
            "recordings": [
                {
                    "id": "I-12:s1",
                    "line_id": "I-12",
                    "block_id": "0.12",
                    "segment_id": "0_12_1",
                    "audio_path": "audio/segments/CENTURION/0_12_1.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "floor_noise_id": "floor-20260511T115900Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={
            "audio/segments/CENTURION/0_12_1.wav": _wav_bytes(),
            "noise/floor-20260511T115900Z.wav": _wav_bytes(b"\x00\x00"),
        },
    )
    audio_processor = FakeAudioProcessor()

    result = RoleRecordingsImporter(paths=cfg, audio_processor=audio_processor).import_package(
        package_path,
        processing_options=RecordingImportProcessingOptions(denoise=True, trim_silence=True),
    )

    assert (cfg.segments_dir / "CENTURION" / "0_12_1.wav").read_bytes() == b"processed wav"
    assert audio_processor.calls[0]["floor_noise_path"].read_bytes() == _wav_bytes(b"\x00\x00")
    assert audio_processor.calls[0]["floor_noise_duration_ms"] == 5000
    assert audio_processor.calls[0]["options"].denoise is True
    transaction = json.loads(result.transaction_manifest_path.read_text(encoding="utf-8"))
    assert transaction["processing"] == {"denoise": True, "trim_silence": True}
    assert transaction["imported"][0]["floor_noise_id"] == "floor-20260511T115900Z"
    assert "original_path" in transaction["imported"][0]


def test_role_recordings_importer_rejects_unknown_floor_noise_reference(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    package_path = tmp_path / "CENTURION.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "recordings": [
                {
                    "id": "I-12:s1",
                    "line_id": "I-12",
                    "block_id": "0.12",
                    "segment_id": "0_12_1",
                    "audio_path": "audio/segments/CENTURION/0_12_1.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "floor_noise_id": "missing-floor",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={"audio/segments/CENTURION/0_12_1.wav": _wav_bytes()},
    )

    with pytest.raises(RuntimeError, match="Unknown floor noise id"):
        RoleRecordingsImporter(paths=cfg).import_package(package_path)


def test_role_recordings_importer_undo_restores_existing_segment(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    existing_path = cfg.segments_dir / "CENTURION" / "0_12_1.wav"
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    existing_path.write_bytes(b"existing wav")
    package_path = tmp_path / "CENTURION.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "recordings": [
                {
                    "id": "I-12:s1",
                    "line_id": "I-12",
                    "block_id": "0.12",
                    "segment_id": "0_12_1",
                    "audio_path": "audio/segments/CENTURION/0_12_1.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={"audio/segments/CENTURION/0_12_1.wav": _wav_bytes(b"\x02\x00")},
    )
    importer = RoleRecordingsImporter(paths=cfg)
    result = importer.import_package(package_path)

    undo_result = importer.undo_import(result.transaction_manifest_path)

    assert undo_result.restored_count == 1
    assert undo_result.removed_count == 0
    assert existing_path.read_bytes() == b"existing wav"


def test_role_recordings_importer_undo_removes_new_segment(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    target_path = cfg.segments_dir / "CENTURION" / "0_12_1.wav"
    package_path = tmp_path / "CENTURION.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "recordings": [
                {
                    "id": "I-12:s1",
                    "line_id": "I-12",
                    "block_id": "0.12",
                    "segment_id": "0_12_1",
                    "audio_path": "audio/segments/CENTURION/0_12_1.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={"audio/segments/CENTURION/0_12_1.wav": _wav_bytes()},
    )
    importer = RoleRecordingsImporter(paths=cfg)
    result = importer.import_package(package_path)

    undo_result = importer.undo_import(result.transaction_manifest_path)

    assert undo_result.restored_count == 0
    assert undo_result.removed_count == 1
    assert not target_path.exists()


def test_role_recordings_importer_undo_rejects_changed_segment(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    target_path = cfg.segments_dir / "CENTURION" / "0_12_1.wav"
    package_path = tmp_path / "CENTURION.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "recordings": [
                {
                    "id": "I-12:s1",
                    "line_id": "I-12",
                    "block_id": "0.12",
                    "segment_id": "0_12_1",
                    "audio_path": "audio/segments/CENTURION/0_12_1.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={"audio/segments/CENTURION/0_12_1.wav": _wav_bytes()},
    )
    importer = RoleRecordingsImporter(paths=cfg)
    result = importer.import_package(package_path)
    target_path.write_bytes(b"later edit")

    with pytest.raises(RuntimeError, match="Refusing to undo changed segment"):
        importer.undo_import(result.transaction_manifest_path)


def test_role_recordings_importer_rejects_path_traversal(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    package_path = tmp_path / "bad.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "recordings": [
                {
                    "id": "I-12:s1",
                    "line_id": "I-12",
                    "block_id": "0.12",
                    "segment_id": "0_12_1",
                    "audio_path": "../0_12_1.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={"../0_12_1.wav": b"fake wav"},
    )

    with pytest.raises(RuntimeError, match="Unsafe audio path"):
        RoleRecordingsImporter(paths=cfg).import_package(package_path)


def test_role_recordings_importer_rejects_wrong_play(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    package_path = tmp_path / "wrong-play.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "other-play", "title": "Other Play"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "recordings": [],
            "missing_segment_ids": [],
        },
        files={},
    )

    with pytest.raises(RuntimeError, match="does not match selected play"):
        RoleRecordingsImporter(paths=cfg).import_package(package_path)


def test_role_recordings_importer_rejects_missing_audio_file(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    package_path = tmp_path / "missing-audio.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "recordings": [
                {
                    "id": "I-12:s1",
                    "line_id": "I-12",
                    "block_id": "0.12",
                    "segment_id": "0_12_1",
                    "audio_path": "audio/segments/CENTURION/0_12_1.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={},
    )

    with pytest.raises(RuntimeError, match="Missing audio file"):
        RoleRecordingsImporter(paths=cfg).import_package(package_path)


def test_role_recordings_importer_rejects_unknown_play_segment(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    package_path = tmp_path / "unknown-segment.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "recordings": [
                {
                    "id": "I-99:s1",
                    "line_id": "I-99",
                    "block_id": "0.99",
                    "segment_id": "0_99_1",
                    "audio_path": "audio/segments/CENTURION/0_99_1.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={"audio/segments/CENTURION/0_99_1.wav": _wav_bytes()},
    )

    with pytest.raises(RuntimeError, match="Unknown segment ids"):
        RoleRecordingsImporter(paths=cfg, play=_play()).import_package(package_path)


def test_role_recordings_importer_accepts_production_ids_and_hashes(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    play = _production_play(cfg, line_text="I won't go another step.")
    block, segment = _production_role_segment(play, "MEGAERA")
    package_path = tmp_path / "MEGAERA.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "MEGAERA", "display_name": "MEGAERA"},
            "recordings": [
                {
                    "id": segment.production_id,
                    "line_id": block.production_id,
                    "block_id": str(block.block_id),
                    "segment_id": str(segment.segment_id),
                    "line_content_hash": block.content_hash,
                    "segment_content_hash": segment.content_hash,
                    "audio_path": f"audio/segments/MEGAERA/{segment.segment_id}.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={f"audio/segments/MEGAERA/{segment.segment_id}.wav": _wav_bytes()},
    )

    result = RoleRecordingsImporter(paths=cfg, play=play).import_package(package_path)

    transaction = json.loads(result.transaction_manifest_path.read_text(encoding="utf-8"))
    assert transaction["imported"][0]["id"] == "I-2:s1"
    assert transaction["imported"][0]["line_content_hash"].startswith("sha256:")
    assert (cfg.segments_dir / "MEGAERA" / f"{segment.segment_id}.wav").exists()


def test_role_recordings_importer_rejects_stale_production_hashes(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    old_play = _production_play(cfg, line_text="I won't go another step.")
    old_block, old_segment = _production_role_segment(old_play, "MEGAERA")
    current_play = _production_play(cfg, line_text="I won't go another inch.")
    package_path = tmp_path / "MEGAERA.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "MEGAERA", "display_name": "MEGAERA"},
            "recordings": [
                {
                    "id": old_segment.production_id,
                    "line_id": old_block.production_id,
                    "block_id": str(old_block.block_id),
                    "segment_id": str(old_segment.segment_id),
                    "line_content_hash": old_block.content_hash,
                    "segment_content_hash": old_segment.content_hash,
                    "audio_path": f"audio/segments/MEGAERA/{old_segment.segment_id}.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={f"audio/segments/MEGAERA/{old_segment.segment_id}.wav": _wav_bytes()},
    )

    with pytest.raises(RuntimeError, match="Unexpected line_content_hash"):
        RoleRecordingsImporter(paths=cfg, play=current_play).import_package(package_path)


def test_role_recordings_importer_rejects_unreadable_wav(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    package_path = tmp_path / "bad-audio.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "recordings": [
                {
                    "id": "I-12:s1",
                    "line_id": "I-12",
                    "block_id": "0.12",
                    "segment_id": "0_12_1",
                    "audio_path": "audio/segments/CENTURION/0_12_1.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={"audio/segments/CENTURION/0_12_1.wav": b"not a wav"},
    )

    with pytest.raises(RuntimeError, match="Unreadable WAV"):
        RoleRecordingsImporter(paths=cfg).import_package(package_path)


def test_role_recordings_importer_reports_audio_quality_issues(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    package_path = tmp_path / "quiet.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "recordings": [
                {
                    "id": "I-12:s1",
                    "line_id": "I-12",
                    "block_id": "0.12",
                    "segment_id": "0_12_1",
                    "audio_path": "audio/segments/CENTURION/0_12_1.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={
            "audio/segments/CENTURION/0_12_1.wav": _wav_bytes_from_samples([0] * 48000),
            "audio/segments/CENTURION/extra.wav": _wav_bytes(),
        },
    )

    result = RoleRecordingsImporter(paths=cfg).import_package(package_path)

    assert {issue.code for issue in result.issues} >= {"silent", "extra_audio"}
    transaction = json.loads(result.transaction_manifest_path.read_text(encoding="utf-8"))
    assert {issue["code"] for issue in transaction["issues"]} >= {"silent", "extra_audio"}


def test_role_recordings_importer_reports_clipped_and_suspicious_duration(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    package_path = tmp_path / "clipped.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "recordings": [
                {
                    "id": "I-12:s1",
                    "line_id": "I-12",
                    "block_id": "0.12",
                    "segment_id": "0_12_1",
                    "audio_path": "audio/segments/CENTURION/0_12_1.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={"audio/segments/CENTURION/0_12_1.wav": _wav_bytes_from_samples([32767])},
    )

    result = RoleRecordingsImporter(paths=cfg).import_package(package_path)

    assert {issue.code for issue in result.issues} >= {"clipped", "suspicious_duration"}


def test_imported_role_recordings_can_be_used_by_playbook_builder(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path)
    play = _play_with_cue_and_response()
    package_path = tmp_path / "CENTURION.role-recordings.zip"
    _write_package(
        package_path,
        manifest={
            "schema_version": 1,
            "package_type": "role_recordings",
            "complete": True,
            "play": {"id": "androcles", "title": "Androcles and the Lion"},
            "role": {"id": "CENTURION", "display_name": "Centurion"},
            "recordings": [
                {
                    "id": "I-2:s1",
                    "line_id": "I-2",
                    "block_id": "0.2",
                    "segment_id": "0_2_1",
                    "audio_path": "audio/segments/CENTURION/0_2_1.wav",
                    "recorded_at": "2026-05-11T12:00:00Z",
                    "duration_ms": 1000,
                    "sample_rate_hz": 48000,
                    "channels": 1,
                    "status": "accepted",
                }
            ],
            "missing_segment_ids": [],
        },
        files={"audio/segments/CENTURION/0_2_1.wav": _wav_bytes_from_samples([1000] * 4800)},
    )
    _write_wav(cfg.segments_dir / "ANDROCLES" / "0_1_1.wav")
    _write_wav(cfg.segments_dir / "_NARRATOR" / "title.wav")

    RoleRecordingsImporter(paths=cfg, play=play).import_package(package_path)
    PlaybookBuilder(play=play, paths=cfg).build()
    manifest = json.loads((cfg.build_dir / "app" / "manifest.json").read_text(encoding="utf-8"))

    centurion = next(role for role in manifest["roles"] if role["id"] == "CENTURION")
    line = centurion["lines"][0]
    assert line["response"]["segments"][0]["audio"]["path"] == "audio/segments/CENTURION/0_2_1.wav"
    assert (cfg.build_dir / "app" / "audio" / "segments" / "CENTURION" / "0_2_1.wav").exists()


def _write_package(package_path: Path, *, manifest: dict, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(package_path, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for name, data in files.items():
            archive.writestr(name, data)


class FakeAudioProcessor:
    def __init__(self) -> None:
        self.calls = []

    def process(
        self,
        *,
        input_path: Path,
        output_path: Path,
        floor_noise_path: Path | None,
        floor_noise_duration_ms: int | None,
        options: RecordingImportProcessingOptions,
    ) -> None:
        self.calls.append(
            {
                "input_path": input_path,
                "output_path": output_path,
                "floor_noise_path": floor_noise_path,
                "floor_noise_duration_ms": floor_noise_duration_ms,
                "options": options,
            }
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"processed wav")


def _wav_bytes(frame: bytes = b"\x01\x00") -> bytes:
    return _wav_bytes_from_samples([int.from_bytes(frame, "little", signed=True)])


def _wav_bytes_from_samples(samples: list[int]) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes(b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples))
    return buffer.getvalue()


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_wav_bytes_from_samples([1000] * 4800))


def _play() -> Play:
    block_id = BlockId(0, 12)
    return Play(
        blocks=[
            RoleBlock(
                block_id=block_id,
                role_names=["CENTURION"],
                callout="CENTURION",
                text="Halt!",
                segments=[
                    SpeechSegment(
                        segment_id=SegmentId(block_id, 1),
                        text="Halt!",
                        role="CENTURION",
                        production_id="I-12:s1",
                    )
                ],
                production_id="I-12",
            )
        ]
    )


def _play_with_cue_and_response() -> Play:
    cue_block_id = BlockId(0, 1)
    response_block_id = BlockId(0, 2)
    return Play(
        blocks=[
            RoleBlock(
                block_id=cue_block_id,
                role_names=["ANDROCLES"],
                callout="ANDROCLES",
                text="Who goes there?",
                segments=[
                    SpeechSegment(
                        segment_id=SegmentId(cue_block_id, 1),
                        text="Who goes there?",
                        role="ANDROCLES",
                        production_id="I-1:s1",
                    )
                ],
                production_id="I-1",
            ),
            RoleBlock(
                block_id=response_block_id,
                role_names=["CENTURION"],
                callout="CENTURION",
                text="A friend.",
                segments=[
                    SpeechSegment(
                        segment_id=SegmentId(response_block_id, 1),
                        text="A friend.",
                        role="CENTURION",
                        production_id="I-2:s1",
                    )
                ],
                production_id="I-2",
            ),
        ]
    )


def _production_play(cfg: paths.PathConfig, *, line_text: str) -> Play:
    cfg.production_markdown.parent.mkdir(parents=True, exist_ok=True)
    cfg.production_markdown.write_text(
        f"""// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# I-0 ACT I
I-1 ANDROCLES: Well, dear, do you want to see one?
I-2 MEGAERA: {line_text}
""",
        encoding="utf-8",
    )
    return ProductionPlayLoader(paths_config=cfg).load()


def _production_role_segment(play: Play, role: str) -> tuple[RoleBlock, SpeechSegment]:
    block = next(
        candidate
        for candidate in play.blocks
        if isinstance(candidate, RoleBlock) and role in candidate.role_names
    )
    segment = next(
        candidate
        for candidate in block.segments
        if isinstance(candidate, SpeechSegment) and candidate.role == role
    )
    return block, segment
