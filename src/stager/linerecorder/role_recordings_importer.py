from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import filecmp
import io
import json
import logging
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import wave
import zipfile

from stager.domain.block import RoleBlock
from stager.domain.play import Play
from stager.domain.segment import SimultaneousSegment, SpeechSegment
from stager.playbook.app_line import AppLine
from stager.shared import paths

logger = logging.getLogger(__name__)
PRODUCTION_ID_RE = re.compile(r"^[A-Z0-9]+(?:\.[A-Z0-9]+)*-[0-9]+(?:\.[0-9]+)?[a-z]?(?::[sdm][0-9]+)?$")


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
    id: str | None
    line_id: str | None
    line_content_hash: str | None
    segment_id: str
    segment_content_hash: str | None
    audio_path: str
    recorded_at: str | None
    floor_noise_id: str | None
    manifest_duration_ms: int
    member: zipfile.ZipInfo
    target_path: Path
    floor_noise: "FloorNoiseImportItem | None" = None


@dataclass
class FloorNoiseImportItem:
    id: str
    audio_path: str
    recorded_at: str
    duration_ms: int
    member: zipfile.ZipInfo
    artifact_path: Path | None = None


@dataclass
class RecordingImportProcessingOptions:
    denoise: bool = False
    trim_silence: bool = False


class RecordingImportAudioProcessor:
    def process(
        self,
        *,
        input_path: Path,
        output_path: Path,
        floor_noise_path: Path | None,
        floor_noise_duration_ms: int | None,
        options: RecordingImportProcessingOptions,
    ) -> None:
        filters = []
        command = ["ffmpeg", "-y"]
        if options.denoise and floor_noise_path is not None and floor_noise_duration_ms is not None:
            floor_noise_seconds = floor_noise_duration_ms / 1000
            command.extend(["-i", str(floor_noise_path), "-i", str(input_path)])
            filter_chain = (
                f"[0:a][1:a]concat=n=2:v=0:a=1,"
                f"asendcmd=0.0 afftdn sn start,"
                f"asendcmd={floor_noise_seconds:.3f} afftdn sn stop,"
                f"afftdn=nr=10:nf=-50,"
                f"atrim=start={floor_noise_seconds:.3f},asetpts=PTS-STARTPTS"
            )
            if options.trim_silence:
                filter_chain += "," + self._silence_trim_filter()
            command.extend(["-filter_complex", filter_chain])
        else:
            command.extend(["-i", str(input_path)])
            if options.trim_silence:
                filters.append(self._silence_trim_filter())
            if filters:
                command.extend(["-af", ",".join(filters)])
        command.extend([str(output_path)])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def _silence_trim_filter(self) -> str:
        return (
            "silenceremove="
            "start_periods=1:start_duration=0.10:start_threshold=-50dB:"
            "stop_periods=1:stop_duration=0.20:stop_threshold=-50dB"
        )


@dataclass(frozen=True)
class ExpectedRecordingSegment:
    id: str | None
    line_id: str
    segment_id: str
    line_content_hash: str | None
    segment_content_hash: str | None


@dataclass
class RoleRecordingsImporter:
    paths: paths.PathConfig
    play: Play | None = None
    audio_processor: RecordingImportAudioProcessor = field(default_factory=RecordingImportAudioProcessor)

    def import_package(
        self,
        package_path: Path,
        processing_options: RecordingImportProcessingOptions | None = None,
    ) -> RoleRecordingsImportResult:
        options = processing_options or RecordingImportProcessingOptions()
        with zipfile.ZipFile(package_path) as archive:
            manifest = self._read_manifest(archive, package_path)
            self._validate_manifest(manifest, package_path)
            role = manifest["role"]["id"]
            floor_noise_items = self._floor_noise_items(archive, manifest, package_path)
            written_paths = []
            import_jobs = []

            for recording in manifest["recordings"]:
                audio_path = recording["audio_path"]
                target_path = self._target_path(role, recording["segment_id"], audio_path)
                import_jobs.append(
                    RoleRecordingImportJob(
                        id=recording.get("id"),
                        line_id=recording.get("line_id"),
                        line_content_hash=recording.get("line_content_hash"),
                        segment_id=recording["segment_id"],
                        segment_content_hash=recording.get("segment_content_hash"),
                        audio_path=audio_path,
                        recorded_at=recording.get("recorded_at"),
                        floor_noise_id=recording.get("floor_noise_id"),
                        manifest_duration_ms=recording["duration_ms"],
                        member=self._audio_member(archive, audio_path, package_path),
                        target_path=target_path,
                    )
                )
            self._assign_floor_noise(import_jobs, floor_noise_items)

            issues = self._analyze_package_audio(archive, import_jobs, package_path)
            issues.extend(self._extra_audio_issues(archive, import_jobs))
            transaction_manifest_path = self._write_import_transaction(
                archive=archive,
                package_path=package_path,
                manifest=manifest,
                import_jobs=import_jobs,
                floor_noise_items=floor_noise_items,
                issues=issues,
                processing_options=options,
            )

            for import_job in import_jobs:
                target_path = import_job.target_path
                incoming_path = transaction_manifest_path.parent / "incoming" / import_job.audio_path
                processed_path = transaction_manifest_path.parent / "processed" / import_job.audio_path
                copy_source_path = incoming_path
                if options.denoise or options.trim_silence:
                    if options.denoise and import_job.floor_noise is None:
                        logger.info("No floor noise available for %s; importing without denoise", import_job.segment_id)
                    self.audio_processor.process(
                        input_path=incoming_path,
                        output_path=processed_path,
                        floor_noise_path=import_job.floor_noise.artifact_path if import_job.floor_noise else None,
                        floor_noise_duration_ms=import_job.floor_noise.duration_ms if import_job.floor_noise else None,
                        options=options,
                    )
                    copy_source_path = processed_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(copy_source_path, target_path)
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
        for missing_segment_id in manifest["missing_segment_ids"]:
            self._validate_production_id(missing_segment_id, "missing_segment_ids", package_path)
        if not isinstance(manifest.get("complete"), bool):
            raise RuntimeError(f"Invalid complete flag in {paths.display_path(package_path)}")

        for recording in manifest["recordings"]:
            self._validate_recording(recording, role, package_path)
        self._validate_floor_noise_recordings(manifest, package_path)
        self._validate_play_segments(manifest, role, package_path)

    def _validate_recording(self, recording: dict, role: str, package_path: Path) -> None:
        self._validate_production_id(recording.get("id"), "id", package_path)
        self._validate_production_id(recording.get("line_id"), "line_id", package_path)
        segment_id = recording.get("segment_id")
        audio_path = recording.get("audio_path")
        if not segment_id or not audio_path:
            raise RuntimeError(f"Invalid recording entry in {paths.display_path(package_path)}")
        if recording.get("status") != "accepted":
            raise RuntimeError(f"Unexpected recording status in {paths.display_path(package_path)}")
        self._target_path(role, segment_id, audio_path)

    def _validate_floor_noise_recordings(self, manifest: dict, package_path: Path) -> None:
        floor_noise_recordings = manifest.get("floor_noise_recordings", [])
        if floor_noise_recordings is None:
            return
        if not isinstance(floor_noise_recordings, list):
            raise RuntimeError(f"Invalid floor_noise_recordings in {paths.display_path(package_path)}")
        floor_noise_ids = set()
        for floor_noise in floor_noise_recordings:
            floor_noise_id = floor_noise.get("id")
            audio_path = floor_noise.get("audio_path")
            if not isinstance(floor_noise_id, str) or not floor_noise_id:
                raise RuntimeError(f"Invalid floor noise id in {paths.display_path(package_path)}")
            if floor_noise_id in floor_noise_ids:
                raise RuntimeError(f"Duplicate floor noise id {floor_noise_id} in {paths.display_path(package_path)}")
            floor_noise_ids.add(floor_noise_id)
            self._validate_relative_zip_path(audio_path, package_path, "floor noise audio path")
            if not isinstance(floor_noise.get("recorded_at"), str):
                raise RuntimeError(f"Invalid floor noise recorded_at in {paths.display_path(package_path)}")
            if not isinstance(floor_noise.get("duration_ms"), int) or floor_noise["duration_ms"] <= 0:
                raise RuntimeError(f"Invalid floor noise duration in {paths.display_path(package_path)}")
        for recording in manifest["recordings"]:
            floor_noise_id = recording.get("floor_noise_id")
            if floor_noise_id is not None and floor_noise_id not in floor_noise_ids:
                raise RuntimeError(
                    f"Unknown floor noise id {floor_noise_id!r} for segment {recording.get('segment_id')} "
                    f"in {paths.display_path(package_path)}"
                )

    def _validate_relative_zip_path(self, value: object, package_path: Path, field_name: str) -> PurePosixPath:
        if not isinstance(value, str) or not value:
            raise RuntimeError(f"Invalid {field_name} in {paths.display_path(package_path)}")
        relative_path = PurePosixPath(value)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise RuntimeError(f"Unsafe {field_name} in {paths.display_path(package_path)}: {value}")
        return relative_path

    def _validate_production_id(self, value: object, field_name: str, package_path: Path) -> None:
        if not isinstance(value, str) or not PRODUCTION_ID_RE.match(value):
            raise RuntimeError(
                f"Invalid {field_name} production id in {paths.display_path(package_path)}: {value!r}"
            )

    def _validate_play_segments(self, manifest: dict, role: str, package_path: Path) -> None:
        if self.play is None:
            return
        expected_segments = self._expected_segments_for_role(role)
        if not expected_segments:
            raise RuntimeError(f"Unknown role {role!r} in {paths.display_path(package_path)}")
        expected_segment_ids = set(expected_segments)
        imported_segment_ids = {recording["segment_id"] for recording in manifest["recordings"]}
        unknown_segment_ids = sorted(imported_segment_ids - expected_segment_ids)
        if unknown_segment_ids:
            raise RuntimeError(
                f"Unknown segment ids for role {role} in {paths.display_path(package_path)}: {', '.join(unknown_segment_ids)}"
            )
        for recording in manifest["recordings"]:
            self._validate_recording_against_play(
                recording=recording,
                expected=expected_segments[recording["segment_id"]],
                package_path=package_path,
            )

    def _expected_segments_for_role(self, role: str) -> dict[str, ExpectedRecordingSegment]:
        assert self.play is not None
        expected: dict[str, ExpectedRecordingSegment] = {}
        for block in self.play.blocks:
            if not isinstance(block, RoleBlock):
                continue
            for segment in block.segments:
                if isinstance(segment, SpeechSegment) and segment.role == role:
                    expected[str(segment.segment_id)] = self._expected_segment(block, segment, role)
                elif isinstance(segment, SimultaneousSegment) and role in segment.roles:
                    expected[str(segment.segment_id)] = self._expected_segment(block, segment, role)
        return expected

    def _expected_segment(
        self,
        block: RoleBlock,
        segment: SpeechSegment | SimultaneousSegment,
        role: str,
    ) -> ExpectedRecordingSegment:
        segment_id = str(segment.segment_id)
        return ExpectedRecordingSegment(
            id=segment.production_id,
            line_id=AppLine.line_id_for(block, role),
            segment_id=segment_id,
            line_content_hash=block.content_hash,
            segment_content_hash=segment.content_hash,
        )

    def _validate_recording_against_play(
        self,
        *,
        recording: dict,
        expected: ExpectedRecordingSegment,
        package_path: Path,
    ) -> None:
        self._validate_required_match(recording, "id", expected.id, package_path)
        self._validate_required_match(recording, "line_id", expected.line_id, package_path)
        self._validate_required_match(recording, "line_content_hash", expected.line_content_hash, package_path)
        self._validate_required_match(recording, "segment_content_hash", expected.segment_content_hash, package_path)

    def _validate_required_match(
        self,
        recording: dict,
        field_name: str,
        expected_value: str | None,
        package_path: Path,
    ) -> None:
        if expected_value is None:
            return
        actual_value = recording.get(field_name)
        if actual_value is None:
            raise RuntimeError(
                f"Missing {field_name} for segment {recording['segment_id']} in {paths.display_path(package_path)}"
            )
        if actual_value != expected_value:
            raise RuntimeError(
                f"Unexpected {field_name} for segment {recording['segment_id']} in {paths.display_path(package_path)}: "
                f"{actual_value!r} != {expected_value!r}"
            )

    def _audio_member(self, archive: zipfile.ZipFile, audio_path: str, package_path: Path) -> zipfile.ZipInfo:
        try:
            return archive.getinfo(audio_path)
        except KeyError as exc:
            raise RuntimeError(
                f"Missing audio file {audio_path} in {paths.display_path(package_path)}"
            ) from exc

    def _floor_noise_items(
        self,
        archive: zipfile.ZipFile,
        manifest: dict,
        package_path: Path,
    ) -> list[FloorNoiseImportItem]:
        items = []
        for floor_noise in manifest.get("floor_noise_recordings", []) or []:
            audio_path = floor_noise["audio_path"]
            try:
                member = archive.getinfo(audio_path)
            except KeyError as exc:
                raise RuntimeError(
                    f"Missing floor noise audio file {audio_path} in {paths.display_path(package_path)}"
                ) from exc
            items.append(
                FloorNoiseImportItem(
                    id=floor_noise["id"],
                    audio_path=audio_path,
                    recorded_at=floor_noise["recorded_at"],
                    duration_ms=floor_noise["duration_ms"],
                    member=member,
                )
            )
        return sorted(items, key=lambda item: item.recorded_at)

    def _assign_floor_noise(
        self,
        import_jobs: list[RoleRecordingImportJob],
        floor_noise_items: list[FloorNoiseImportItem],
    ) -> None:
        floor_noise_by_id = {floor_noise.id: floor_noise for floor_noise in floor_noise_items}
        for import_job in import_jobs:
            if import_job.floor_noise_id is not None:
                import_job.floor_noise = floor_noise_by_id[import_job.floor_noise_id]
                continue
            if import_job.recorded_at is None:
                continue
            candidates = [
                floor_noise
                for floor_noise in floor_noise_items
                if floor_noise.recorded_at <= import_job.recorded_at
            ]
            if candidates:
                import_job.floor_noise = candidates[-1]

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
        floor_noise_items: list[FloorNoiseImportItem],
        issues: list[RoleRecordingImportIssue],
        processing_options: RecordingImportProcessingOptions,
    ) -> Path:
        transaction_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        transaction_dir = self.paths.build_dir / "linerecorder" / "imports" / transaction_id
        imported = []

        for floor_noise in floor_noise_items:
            artifact_path = transaction_dir / "floor_noise" / floor_noise.audio_path
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(floor_noise.member) as source, artifact_path.open("wb") as target:
                target.write(source.read())
            floor_noise.artifact_path = artifact_path

        for import_job in import_jobs:
            original_path = transaction_dir / "original" / import_job.audio_path
            incoming_path = transaction_dir / "incoming" / import_job.audio_path
            backup_path = transaction_dir / "backups" / import_job.audio_path
            existed_before = import_job.target_path.exists()

            original_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(import_job.member) as source, original_path.open("wb") as target:
                target.write(source.read())
            incoming_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original_path, incoming_path)

            if existed_before:
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(import_job.target_path, backup_path)

            item = {
                "segment_id": import_job.segment_id,
                "target_path": import_job.audio_path,
                "incoming_path": paths.display_path(incoming_path),
                "original_path": paths.display_path(original_path),
                "existed_before": existed_before,
            }
            self._put_optional(item, "id", import_job.id)
            self._put_optional(item, "line_id", import_job.line_id)
            self._put_optional(item, "line_content_hash", import_job.line_content_hash)
            self._put_optional(item, "segment_content_hash", import_job.segment_content_hash)
            self._put_optional(item, "floor_noise_id", import_job.floor_noise.id if import_job.floor_noise else None)
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
                    "processing": {
                        "denoise": processing_options.denoise,
                        "trim_silence": processing_options.trim_silence,
                    },
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

    def _put_optional(self, item: dict, key: str, value: str | None) -> None:
        if value is not None:
            item[key] = value

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
