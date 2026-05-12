from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import filecmp
import json
import logging
from pathlib import Path, PurePosixPath
import shutil
import zipfile

from stager.shared import paths

logger = logging.getLogger(__name__)


@dataclass
class RoleRecordingsImportResult:
    role: str
    imported_count: int
    missing_segment_ids: list[str]
    complete: bool
    transaction_manifest_path: Path
    written_paths: list[Path] = field(default_factory=list)


@dataclass
class RoleRecordingsUndoResult:
    role: str
    restored_count: int
    removed_count: int


@dataclass
class RoleRecordingImportJob:
    segment_id: str
    audio_path: str
    member: zipfile.ZipInfo
    target_path: Path


@dataclass
class RoleRecordingsImporter:
    paths: paths.PathConfig

    def import_package(self, package_path: Path) -> RoleRecordingsImportResult:
        with zipfile.ZipFile(package_path) as archive:
            manifest = self._read_manifest(archive, package_path)
            self._validate_manifest(manifest, package_path)
            role = manifest["role"]["id"]
            written_paths = []
            import_jobs = []

            for recording in manifest["recordings"]:
                audio_path = recording["audio_path"]
                target_path = self._target_path(role, recording["segment_id"], audio_path)
                import_jobs.append(
                    RoleRecordingImportJob(
                        segment_id=recording["segment_id"],
                        audio_path=audio_path,
                        member=self._audio_member(archive, audio_path, package_path),
                        target_path=target_path,
                    )
                )

            transaction_manifest_path = self._write_import_transaction(
                archive=archive,
                package_path=package_path,
                manifest=manifest,
                import_jobs=import_jobs,
            )

            for import_job in import_jobs:
                target_path = import_job.target_path
                incoming_path = transaction_manifest_path.parent / "incoming" / import_job.audio_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(incoming_path, target_path)
                written_paths.append(target_path)
                logger.info("Imported LineRecorder segment %s", paths.display_path(target_path))

        return RoleRecordingsImportResult(
            role=role,
            imported_count=len(written_paths),
            missing_segment_ids=list(manifest.get("missing_segment_ids", [])),
            complete=bool(manifest["complete"]),
            transaction_manifest_path=transaction_manifest_path,
            written_paths=written_paths,
        )

    def undo_import(self, transaction_manifest_path: Path) -> RoleRecordingsUndoResult:
        transaction = json.loads(transaction_manifest_path.read_text(encoding="utf-8"))
        if transaction.get("play_id") != self.paths.play_name:
            raise RuntimeError(
                f"Import transaction play id {transaction.get('play_id')!r} does not match selected play {self.paths.play_name!r}"
            )
        if not isinstance(transaction.get("imported"), list):
            raise RuntimeError(f"Invalid import transaction: {paths.display_path(transaction_manifest_path)}")

        restored_count = 0
        removed_count = 0
        for imported in transaction["imported"]:
            target_path = self._transaction_target_path(imported["target_path"])
            incoming_path = self._transaction_artifact_path(imported["incoming_path"], transaction_manifest_path)
            if target_path.exists() and not filecmp.cmp(target_path, incoming_path, shallow=False):
                raise RuntimeError(f"Refusing to undo changed segment: {paths.display_path(target_path)}")

            if imported["existed_before"]:
                backup_path = self._transaction_artifact_path(imported["backup_path"], transaction_manifest_path)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_path, target_path)
                restored_count += 1
                logger.info("Restored LineRecorder import backup %s", paths.display_path(target_path))
            else:
                if target_path.exists():
                    target_path.unlink()
                    removed_count += 1
                    logger.info("Removed LineRecorder imported segment %s", paths.display_path(target_path))

        return RoleRecordingsUndoResult(
            role=transaction["role_id"],
            restored_count=restored_count,
            removed_count=removed_count,
        )

    def _read_manifest(self, archive: zipfile.ZipFile, package_path: Path) -> dict:
        try:
            with archive.open("manifest.json") as manifest_file:
                return json.loads(manifest_file.read().decode("utf-8"))
        except KeyError as exc:
            raise RuntimeError(f"Missing manifest.json in {paths.display_path(package_path)}") from exc

    def _validate_manifest(self, manifest: dict, package_path: Path) -> None:
        if manifest.get("schema_version") != 1:
            raise RuntimeError(f"Unsupported role recordings schema in {paths.display_path(package_path)}")
        if manifest.get("package_type") != "role_recordings":
            raise RuntimeError(f"Expected role_recordings package: {paths.display_path(package_path)}")
        if manifest.get("play", {}).get("id") != self.paths.play_name:
            raise RuntimeError(
                f"Package play id {manifest.get('play', {}).get('id')!r} does not match selected play {self.paths.play_name!r}"
            )
        role = manifest.get("role", {}).get("id")
        if not role:
            raise RuntimeError(f"Missing role id in {paths.display_path(package_path)}")
        if not isinstance(manifest.get("recordings"), list):
            raise RuntimeError(f"Invalid recordings list in {paths.display_path(package_path)}")
        if not isinstance(manifest.get("missing_segment_ids"), list):
            raise RuntimeError(f"Invalid missing_segment_ids in {paths.display_path(package_path)}")
        if not isinstance(manifest.get("complete"), bool):
            raise RuntimeError(f"Invalid complete flag in {paths.display_path(package_path)}")

        for recording in manifest["recordings"]:
            self._validate_recording(recording, role, package_path)

    def _validate_recording(self, recording: dict, role: str, package_path: Path) -> None:
        segment_id = recording.get("segment_id")
        audio_path = recording.get("audio_path")
        if not segment_id or not audio_path:
            raise RuntimeError(f"Invalid recording entry in {paths.display_path(package_path)}")
        if recording.get("status") != "accepted":
            raise RuntimeError(f"Unexpected recording status in {paths.display_path(package_path)}")
        self._target_path(role, segment_id, audio_path)

    def _audio_member(self, archive: zipfile.ZipFile, audio_path: str, package_path: Path) -> zipfile.ZipInfo:
        try:
            return archive.getinfo(audio_path)
        except KeyError as exc:
            raise RuntimeError(
                f"Missing audio file {audio_path} in {paths.display_path(package_path)}"
            ) from exc

    def _write_import_transaction(
        self,
        *,
        archive: zipfile.ZipFile,
        package_path: Path,
        manifest: dict,
        import_jobs: list[RoleRecordingImportJob],
    ) -> Path:
        transaction_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        transaction_dir = self.paths.build_dir / "linerecorder" / "imports" / transaction_id
        imported = []

        for import_job in import_jobs:
            incoming_path = transaction_dir / "incoming" / import_job.audio_path
            backup_path = transaction_dir / "backups" / import_job.audio_path
            existed_before = import_job.target_path.exists()

            incoming_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(import_job.member) as source, incoming_path.open("wb") as target:
                target.write(source.read())

            if existed_before:
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(import_job.target_path, backup_path)

            item = {
                "segment_id": import_job.segment_id,
                "target_path": import_job.audio_path,
                "incoming_path": paths.display_path(incoming_path),
                "existed_before": existed_before,
            }
            if existed_before:
                item["backup_path"] = paths.display_path(backup_path)
            imported.append(item)

        transaction_manifest_path = transaction_dir / "import.json"
        transaction_manifest_path.write_text(
            json.dumps(
                {
                    "id": transaction_id,
                    "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "source_package": paths.display_path(package_path),
                    "play_id": manifest["play"]["id"],
                    "role_id": manifest["role"]["id"],
                    "complete": manifest["complete"],
                    "missing_segment_ids": list(manifest.get("missing_segment_ids", [])),
                    "imported": imported,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        logger.info("Wrote LineRecorder import transaction %s", paths.display_path(transaction_manifest_path))
        return transaction_manifest_path

    def _transaction_target_path(self, target_path: str) -> Path:
        relative_path = PurePosixPath(target_path)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise RuntimeError(f"Unsafe target path in import transaction: {target_path}")
        return self.paths.build_dir / Path(relative_path)

    def _transaction_artifact_path(self, artifact_path: str, transaction_manifest_path: Path) -> Path:
        path = Path(artifact_path)
        if path.is_absolute():
            candidate = path
        else:
            candidate = paths.project_root() / path
        transaction_dir = transaction_manifest_path.parent.resolve()
        try:
            candidate.resolve().relative_to(transaction_dir)
        except ValueError as exc:
            raise RuntimeError(f"Import transaction artifact outside transaction: {artifact_path}") from exc
        return candidate

    def _target_path(self, role: str, segment_id: str, audio_path: str) -> Path:
        relative_path = PurePosixPath(audio_path)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise RuntimeError(f"Unsafe audio path in role recordings package: {audio_path}")
        expected = PurePosixPath("audio") / "segments" / role / f"{segment_id}.wav"
        if relative_path != expected:
            raise RuntimeError(f"Unexpected audio path for segment {segment_id}: {audio_path}")
        return self.paths.segments_dir / role / f"{segment_id}.wav"
