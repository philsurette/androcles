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
from stager.linerecorder.role_recordings_importer import RoleRecordingsImporter
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
                    "line_id": "0_12_CENTURION",
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
            "missing_segment_ids": ["0_14_1"],
        },
        files={"audio/segments/CENTURION/0_12_1.wav": _wav_bytes()},
    )

    result = RoleRecordingsImporter(paths=cfg).import_package(package_path)

    assert result.role == "CENTURION"
    assert result.imported_count == 1
    assert result.complete is False
    assert result.missing_segment_ids == ["0_14_1"]
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
                    "line_id": "0_12_CENTURION",
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
                    "line_id": "0_12_CENTURION",
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
                    "line_id": "0_12_CENTURION",
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
                    "line_id": "0_12_CENTURION",
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
                    "line_id": "0_12_CENTURION",
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
                    "line_id": "0_12_CENTURION",
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
                    "line_id": "0_12_CENTURION",
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
                    "line_id": "0_99_CENTURION",
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
                    "line_id": "0_12_CENTURION",
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


def _write_package(package_path: Path, *, manifest: dict, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(package_path, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for name, data in files.items():
            archive.writestr(name, data)


def _wav_bytes(frame: bytes = b"\x01\x00") -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes(frame)
    return buffer.getvalue()


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
                    )
                ],
            )
        ]
    )
