from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import filecmp
import io
import json
import logging
from pathlib import Path, PurePosixPath
import shutil
import wave
import zipfile

from stager.domain.play import Play
from stager.shared import paths

logger = logging.getLogger(__name__)


@dataclass
class RoleRecordingsImportResult:
    role: str
    imported_count: int
    missing_segment_ids: list[str]
    complete: bool
    transaction_manifest_path: Path
    issues: list["RoleRecordingImportIssue"] = field(default_factory=list)
    written_paths: list[Path] = field(default_factory=list)


@dataclass
class RoleRecordingsUndoResult:
    role: str
    restored_count: int
    removed_count: int


@dataclass
class RoleRecordingImportIssue:
    code: str
    message: str
    segment_id: str | None = None

    def to_dict(self) -> dict[str, str]:
        data = {
            "code": self.code,
            "message": self.message,
        }
        if self.segment_id is not None:
            data["segment_id"] = self.segment_id
        return data


@dataclass
class RoleRecordingImportJob:
    segment_id: str
    audio_path: str
    manifest_duration_ms: int
    member: zipfile.ZipInfo
    target_path: Path


@dataclass
class RoleRecordingsImporter:
    paths: paths.PathConfig
    play: Play | None = None

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
                        manifest_duration_ms=recording["duration_ms"],
                        member=self._audio_member(archive, audio_path, package_path),
                        target_path=target_path,
                    )
                )

            issues = self._analyze_package_audio(archive, import_jobs, package_path)
            issues.extend(self._extra_audio_issues(archive, import_jobs))
            transaction_manifest_path = self._write_import_transaction(
                archive=archive,
                package_path=package_path,
                manifest=manifest,
                import_jobs=import_jobs,
                issues=issues,
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
            issues=issues,
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
        self._validate_play_segments(manifest, role, package_path)

    def _validate_recording(self, recording: dict, role: str, package_path: Path) -> None:
        segment_id = recording.get("segment_id")
        audio_path = recording.get("audio_path")
        if not segment_id or not audio_path:
            raise RuntimeError(f"Invalid recording entry in {paths.display_path(package_path)}")
        if recording.get("status") != "accepted":
            raise RuntimeError(f"Unexpected recording status in {paths.display_path(package_path)}")
        self._target_path(role, segment_id, audio_path)

    def _validate_play_segments(self, manifest: dict, role: str, package_path: Path) -> None:
        if self.play is None:
            return
        segment_maps = self.play.build_segment_maps()
        if role not in segment_maps:
            raise RuntimeError(f"Unknown role {role!r} in {paths.display_path(package_path)}")
        expected_segment_ids = {
            segment_id
            for segment_ids in segment_maps[role].values()
            for segment_id in segment_ids
        }
        imported_segment_ids = {recording["segment_id"] for recording in manifest["recordings"]}
        unknown_segment_ids = sorted(imported_segment_ids - expected_segment_ids)
        if unknown_segment_ids:
            raise RuntimeError(
                f"Unknown segment ids for role {role} in {paths.display_path(package_path)}: {', '.join(unknown_segment_ids)}"
            )

    def _audio_member(self, archive: zipfile.ZipFile, audio_path: str, package_path: Path) -> zipfile.ZipInfo:
        try:
            return archive.getinfo(audio_path)
        except KeyError as exc:
            raise RuntimeError(
                f"Missing audio file {audio_path} in {paths.display_path(package_path)}"
            ) from exc

    def _analyze_package_audio(
        self,
        archive: zipfile.ZipFile,
        import_jobs: list[RoleRecordingImportJob],
        package_path: Path,
    ) -> list[RoleRecordingImportIssue]:
        issues = []
        for import_job in import_jobs:
            with archive.open(import_job.member) as source:
                audio_bytes = source.read()
            try:
                with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
                    if wav.getnchannels() < 1:
                        raise RuntimeError(
                            f"Invalid WAV channel count for segment {import_job.segment_id} in {paths.display_path(package_path)}"
                        )
                    if wav.getframerate() < 1:
                        raise RuntimeError(
                            f"Invalid WAV sample rate for segment {import_job.segment_id} in {paths.display_path(package_path)}"
                        )
                    if wav.getnframes() < 1:
                        raise RuntimeError(
                            f"Empty WAV for segment {import_job.segment_id} in {paths.display_path(package_path)}"
                        )
                    channels = wav.getnchannels()
                    sample_width = wav.getsampwidth()
                    sample_rate = wav.getframerate()
                    frame_count = wav.getnframes()
                    frames = wav.readframes(frame_count)
            except wave.Error as exc:
                raise RuntimeError(
                    f"Unreadable WAV for segment {import_job.segment_id} in {paths.display_path(package_path)}"
                ) from exc
            issues.extend(
                self._audio_quality_issues(
                    import_job=import_job,
                    channels=channels,
                    sample_width=sample_width,
                    sample_rate=sample_rate,
                    frame_count=frame_count,
                    frames=frames,
                )
            )
        return issues

    def _audio_quality_issues(
        self,
        *,
        import_job: RoleRecordingImportJob,
        channels: int,
        sample_width: int,
        sample_rate: int,
        frame_count: int,
        frames: bytes,
    ) -> list[RoleRecordingImportIssue]:
        issues = []
        duration_ms = round(frame_count / sample_rate * 1000)
        duration_delta_ms = abs(duration_ms - import_job.manifest_duration_ms)
        if duration_delta_ms > 250 and duration_delta_ms > max(250, import_job.manifest_duration_ms * 0.2):
            issues.append(
                RoleRecordingImportIssue(
                    code="suspicious_duration",
                    segment_id=import_job.segment_id,
                    message=(
                        f"{import_job.segment_id} manifest duration {import_job.manifest_duration_ms} ms "
                        f"differs from WAV duration {duration_ms} ms"
                    ),
                )
            )

        samples = self._normalized_samples(frames, sample_width)
        if not samples:
            return issues
        peak = max(abs(sample) for sample in samples)
        rms = (sum(sample * sample for sample in samples) / len(samples)) ** 0.5
        clipped_count = sum(1 for sample in samples if abs(sample) >= 0.999)
        if peak <= 0.0001:
            issues.append(
                RoleRecordingImportIssue(
                    code="silent",
                    segment_id=import_job.segment_id,
                    message=f"{import_job.segment_id} appears silent",
                )
            )
        elif rms < 0.01:
            issues.append(
                RoleRecordingImportIssue(
                    code="too_quiet",
                    segment_id=import_job.segment_id,
                    message=f"{import_job.segment_id} appears too quiet",
                )
            )
        if clipped_count / len(samples) >= 0.01:
            issues.append(
                RoleRecordingImportIssue(
                    code="clipped",
                    segment_id=import_job.segment_id,
                    message=f"{import_job.segment_id} appears clipped",
                )
            )
        if channels > 1:
            issues.append(
                RoleRecordingImportIssue(
                    code="unexpected_channels",
                    segment_id=import_job.segment_id,
                    message=f"{import_job.segment_id} has {channels} channels",
                )
            )
        return issues

    def _normalized_samples(self, frames: bytes, sample_width: int) -> list[float]:
        samples = []
        for offset in range(0, len(frames), sample_width):
            sample_bytes = frames[offset : offset + sample_width]
            if len(sample_bytes) != sample_width:
                break
            if sample_width == 1:
                sample = (sample_bytes[0] - 128) / 128
            elif sample_width == 2:
                sample = int.from_bytes(sample_bytes, "little", signed=True) / 32768
            elif sample_width == 3:
                sample = int.from_bytes(sample_bytes + (b"\xff" if sample_bytes[-1] & 0x80 else b"\x00"), "little", signed=True) / 8388608
            elif sample_width == 4:
                sample = int.from_bytes(sample_bytes, "little", signed=True) / 2147483648
            else:
                return []
            samples.append(sample)
        return samples

    def _extra_audio_issues(
        self,
        archive: zipfile.ZipFile,
        import_jobs: list[RoleRecordingImportJob],
    ) -> list[RoleRecordingImportIssue]:
        expected_paths = {import_job.audio_path for import_job in import_jobs}
        return [
            RoleRecordingImportIssue(
                code="extra_audio",
                message=f"Package contains unreferenced audio file {name}",
            )
            for name in archive.namelist()
            if name.startswith("audio/") and name.endswith(".wav") and name not in expected_paths
        ]

    def _write_import_transaction(
        self,
        *,
        archive: zipfile.ZipFile,
        package_path: Path,
        manifest: dict,
        import_jobs: list[RoleRecordingImportJob],
        issues: list[RoleRecordingImportIssue],
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
                    "issues": [issue.to_dict() for issue in issues],
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
