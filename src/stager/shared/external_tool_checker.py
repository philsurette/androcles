from __future__ import annotations

from dataclasses import dataclass
import platform
import shutil


@dataclass(frozen=True)
class ExternalToolChecker:
    tools: tuple[str, ...] = ("ffmpeg", "ffprobe")

    def require_audio_tools(self) -> None:
        missing = [tool for tool in self.tools if shutil.which(tool) is None]
        if missing:
            raise RuntimeError(
                "Missing required audio tool(s): "
                f"{', '.join(missing)}. Install ffmpeg and make sure ffmpeg and ffprobe are on PATH.\n"
                f"{self._install_hint()}"
            )

    def _install_hint(self) -> str:
        system = platform.system()
        if system == "Darwin":
            return "macOS: install ffmpeg with Homebrew (`brew install ffmpeg`) or another trusted ffmpeg package."
        if system == "Windows":
            return "Windows: install ffmpeg from a trusted distribution and add its bin directory to PATH."
        return "Linux: install ffmpeg with your system package manager, such as `apt install ffmpeg`."
