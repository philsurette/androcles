from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    backup_manifest_path: Path | None = None
    written_paths: list[Path] = field(default_factory=list)


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

            backup_manifest_path = self._backup_existing_segments(
                package_path=package_path,
                manifest=manifest,
                import_jobs=import_jobs,
            )

            for import_job in import_jobs:
                target_path = import_job.target_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(import_job.member) as source, target_path.open("wb") as target:
                    target.write(source.read())
                written_paths.append(target_path)
                logger.info("Imported LineRecorder segment %s", paths.display_path(target_path))

        return RoleRecordingsImportResult(
            role=role,
            imported_count=len(written_paths),
            missing_segment_ids=list(manifest.get("missing_segment_ids", [])),
            complete=bool(manifest["complete"]),
            backup_manifest_path=backup_manifest_path,
            written_paths=written_paths,
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

    def _backup_existing_segments(
        self,
        *,
        package_path: Path,
        manifest: dict,
        import_jobs: list[RoleRecordingImportJob],
    ) -> Path | None:
        replacements = [import_job for import_job in import_jobs if import_job.target_path.exists()]
        if not replacements:
            return None

        backup_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_dir = self.paths.build_dir / "linerecorder" / "import_backups" / backup_id
        replaced = []

        for import_job in replacements:
            backup_path = backup_dir / import_job.audio_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(import_job.target_path, backup_path)
            replaced.append(
                {
                    "segment_id": import_job.segment_id,
                    "original_path": import_job.audio_path,
                    "backup_path": paths.display_path(backup_path),
                }
            )

        backup_manifest_path = backup_dir / "manifest.json"
        backup_manifest_path.write_text(
            json.dumps(
                {
                    "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "source_package": paths.display_path(package_path),
                    "play_id": manifest["play"]["id"],
                    "role_id": manifest["role"]["id"],
                    "replaced": replaced,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        logger.info("Backed up LineRecorder import replacements to %s", paths.display_path(backup_manifest_path))
        return backup_manifest_path

    def _target_path(self, role: str, segment_id: str, audio_path: str) -> Path:
        relative_path = PurePosixPath(audio_path)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise RuntimeError(f"Unsafe audio path in role recordings package: {audio_path}")
        expected = PurePosixPath("audio") / "segments" / role / f"{segment_id}.wav"
        if relative_path != expected:
            raise RuntimeError(f"Unexpected audio path for segment {segment_id}: {audio_path}")
        return self.paths.segments_dir / role / f"{segment_id}.wav"
