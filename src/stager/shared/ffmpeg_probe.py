from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import shutil
import subprocess


logger = logging.getLogger(__name__)

REQUIRED_VOICE_PROFILE_FILTERS = (
    "aresample",
    "asetrate",
    "atempo",
    "highpass",
    "lowpass",
    "equalizer",
    "acompressor",
    "volume",
    "alimiter",
    "aecho",
    "atrim",
    "asetpts",
    "concat",
    "loudnorm",
)
OPTIONAL_VOICE_PROFILE_FILTERS = (
    "adeclick",
    "deesser",
    "afftdn",
    "afwtdn",
    "anlmdn",
    "agate",
    "firequalizer",
    "afir",
)


@dataclass(frozen=True)
class FfmpegConfig:
    path: Path
    bin_dir: Path


@dataclass(frozen=True)
class FfmpegInstallation:
    ffmpeg_path: Path
    ffprobe_path: Path
    source: str
    config_path: Path | None
    filters: frozenset[str]

    def has_filter(self, name: str) -> bool:
        return name in self.filters

    def missing_required_voice_profile_filters(self) -> list[str]:
        return [name for name in REQUIRED_VOICE_PROFILE_FILTERS if name not in self.filters]

    def optional_voice_profile_filter_report(self) -> dict[str, bool]:
        return {name: name in self.filters for name in OPTIONAL_VOICE_PROFILE_FILTERS}


@dataclass
class FfmpegProbe:
    working_dir: Path = Path.cwd()
    home_dir: Path = Path.home()

    def find_installation(self) -> FfmpegInstallation:
        config = self._read_config()
        if config is not None:
            return self._from_config(config)
        logger.warning(
            "No Quince FFmpeg config file found; falling back to ffmpeg and ffprobe on PATH."
        )
        return self._from_path()

    def _read_config(self) -> FfmpegConfig | None:
        for path in self._config_candidates():
            if path.exists():
                return self._parse_config(path)
        return None

    def _config_candidates(self) -> list[Path]:
        return [
            self.working_dir / ".quince" / "ffmpeg.conf",
            self.home_dir / ".config" / "quince" / "ffmpeg.conf",
        ]

    def _parse_config(self, path: Path) -> FfmpegConfig:
        values = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise RuntimeError(f"Invalid FFmpeg config line in {path}: {raw_line}")
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
        raw_bin_dir = values.get("ffmpeg_bin_dir")
        if raw_bin_dir is None:
            raise RuntimeError(f"Missing ffmpeg_bin_dir in FFmpeg config: {path}")
        return FfmpegConfig(path=path, bin_dir=Path(raw_bin_dir).expanduser())

    def _from_config(self, config: FfmpegConfig) -> FfmpegInstallation:
        ffmpeg_path = config.bin_dir / self._executable_name("ffmpeg")
        ffprobe_path = config.bin_dir / self._executable_name("ffprobe")
        missing = [str(path) for path in (ffmpeg_path, ffprobe_path) if not path.exists()]
        if missing:
            raise RuntimeError(
                f"Configured FFmpeg tool(s) not found from {config.path}: {', '.join(missing)}"
            )
        self._prepend_path(config.bin_dir)
        logger.info("Using FFmpeg from config %s: %s", config.path, config.bin_dir)
        return self._installation(
            ffmpeg_path=ffmpeg_path,
            ffprobe_path=ffprobe_path,
            source="config",
            config_path=config.path,
        )

    def _from_path(self) -> FfmpegInstallation:
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        missing = [tool for tool, resolved in (("ffmpeg", ffmpeg), ("ffprobe", ffprobe)) if resolved is None]
        if missing:
            raise RuntimeError(f"Missing required audio tool(s): {', '.join(missing)}")
        assert ffmpeg is not None
        assert ffprobe is not None
        return self._installation(
            ffmpeg_path=Path(ffmpeg),
            ffprobe_path=Path(ffprobe),
            source="PATH",
            config_path=None,
        )

    def _installation(
        self,
        *,
        ffmpeg_path: Path,
        ffprobe_path: Path,
        source: str,
        config_path: Path | None,
    ) -> FfmpegInstallation:
        filters = self._filters(ffmpeg_path)
        installation = FfmpegInstallation(
            ffmpeg_path=ffmpeg_path,
            ffprobe_path=ffprobe_path,
            source=source,
            config_path=config_path,
            filters=frozenset(filters),
        )
        logger.info("Using ffmpeg: %s", ffmpeg_path)
        logger.info("Using ffprobe: %s", ffprobe_path)
        self._log_filter_report(installation)
        return installation

    def _filters(self, ffmpeg_path: Path) -> set[str]:
        result = subprocess.run(
            [str(ffmpeg_path), "-hide_banner", "-filters"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = (result.stderr or "").strip()
            suffix = f": {detail}" if detail else ""
            raise RuntimeError(f"Failed to inspect FFmpeg filters with {ffmpeg_path}{suffix}")
        filters = set()
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].startswith(("T", ".", "S", "C", "A", "V", "N", "|")):
                filters.add(parts[1])
        return filters

    def _log_filter_report(self, installation: FfmpegInstallation) -> None:
        for name in REQUIRED_VOICE_PROFILE_FILTERS:
            logger.info("FFmpeg required filter %s: %s", name, "found" if installation.has_filter(name) else "missing")
        for name, found in installation.optional_voice_profile_filter_report().items():
            logger.info("FFmpeg optional filter %s: %s", name, "found" if found else "not found")

    def _prepend_path(self, bin_dir: Path) -> None:
        current = os.environ.get("PATH", "")
        parts = current.split(os.pathsep) if current else []
        bin_dir_text = str(bin_dir)
        if parts and parts[0] == bin_dir_text:
            return
        os.environ["PATH"] = os.pathsep.join([bin_dir_text, *[part for part in parts if part != bin_dir_text]])

    def _executable_name(self, name: str) -> str:
        return f"{name}.exe" if os.name == "nt" else name
