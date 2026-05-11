from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import shutil

from pydub import AudioSegment

from stager.shared import paths


@dataclass
class PackagedAudio:
    path: Path
    manifest_path: PurePosixPath


@dataclass
class PlaybookAudioPackager:
    app_dir: Path
    audio_format: str = "wav"
    mp3_bitrate: str = "128k"

    def __post_init__(self) -> None:
        if self.audio_format not in ("wav", "mp3"):
            raise ValueError("audio_format must be one of: wav, mp3")

    def package(self, source_path: Path, destination_dir: Path) -> PackagedAudio:
        destination = destination_dir / source_path.with_suffix(f".{self.audio_format}").name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if self.audio_format == "wav":
            shutil.copy2(source_path, destination)
        else:
            self._export_mp3(source_path, destination)
        return PackagedAudio(
            path=destination,
            manifest_path=PurePosixPath(destination.relative_to(self.app_dir).as_posix()),
        )

    def _export_mp3(self, source_path: Path, destination: Path) -> None:
        try:
            AudioSegment.from_file(source_path).export(
                destination,
                format="mp3",
                bitrate=self.mp3_bitrate,
            )
        except Exception as exc:
            raise RuntimeError(
                "Unable to export Playbook MP3 asset "
                f"{paths.display_path(source_path)} to {paths.display_path(destination)}"
            ) from exc
