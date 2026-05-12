from __future__ import annotations

import json
from pathlib import Path
import zipfile

import pytest

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
        files={"audio/segments/CENTURION/0_12_1.wav": b"fake wav"},
    )

    result = RoleRecordingsImporter(paths=cfg).import_package(package_path)

    assert result.role == "CENTURION"
    assert result.imported_count == 1
    assert result.complete is False
    assert result.missing_segment_ids == ["0_14_1"]
    assert (cfg.segments_dir / "CENTURION" / "0_12_1.wav").read_bytes() == b"fake wav"


def test_role_recordings_importer_backs_up_existing_segment_before_overwrite(tmp_path: Path) -> None:
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
        files={"audio/segments/CENTURION/0_12_1.wav": b"replacement wav"},
    )

    result = RoleRecordingsImporter(paths=cfg).import_package(package_path)

    assert existing_path.read_bytes() == b"replacement wav"
    assert result.backup_manifest_path is not None
    backup_manifest = json.loads(result.backup_manifest_path.read_text(encoding="utf-8"))
    assert backup_manifest["source_package"] == package_path.as_posix()
    assert backup_manifest["replaced"][0]["segment_id"] == "0_12_1"
    backup_path = result.backup_manifest_path.parent / "audio" / "segments" / "CENTURION" / "0_12_1.wav"
    assert backup_path.read_bytes() == b"existing wav"


def test_role_recordings_importer_skips_backup_when_target_is_new(tmp_path: Path) -> None:
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
        files={"audio/segments/CENTURION/0_12_1.wav": b"new wav"},
    )

    result = RoleRecordingsImporter(paths=cfg).import_package(package_path)

    assert result.backup_manifest_path is None
    assert not (cfg.build_dir / "linerecorder" / "import_backups").exists()


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


def _write_package(package_path: Path, *, manifest: dict, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(package_path, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for name, data in files.items():
            archive.writestr(name, data)
