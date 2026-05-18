from __future__ import annotations

from dataclasses import dataclass
import platform
from pathlib import Path

from stager.shared.ffmpeg_probe import FfmpegInstallation, FfmpegProbe


@dataclass(frozen=True)
class ExternalToolChecker:
    working_dir: Path | None = None
    probe: FfmpegProbe | None = None

    def require_audio_tools(self) -> FfmpegInstallation:
        try:
            probe = self.probe or FfmpegProbe(working_dir=self.working_dir or Path.cwd())
            return probe.find_installation()
        except RuntimeError as exc:
            raise RuntimeError(
                f"{exc}. Install ffmpeg and make sure ffmpeg and ffprobe are available through "
                "a Quince ffmpeg.conf file or on PATH.\n"
                f"{self._install_hint()}"
            ) from exc

    def _install_hint(self) -> str:
        system = platform.system()
        if system == "Darwin":
            return "macOS: install ffmpeg with Homebrew (`brew install ffmpeg`) or another trusted ffmpeg package."
        if system == "Windows":
            return "Windows: install ffmpeg from a trusted distribution and add its bin directory to PATH."
        return "Linux: install ffmpeg with your system package manager, such as `apt install ffmpeg`."
