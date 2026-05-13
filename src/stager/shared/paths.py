from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict

from stager.shared.play_config import DEFAULT_PLAY_ID, PlayConfig

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLAY_NAME = DEFAULT_PLAY_ID


def default_play_name() -> str:
    return PlayConfig.load().play_id


def project_root() -> Path:
    return ROOT.parent


def display_path(path: Path | str) -> str:
    path = Path(path)
    root = project_root().resolve()
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def display_location(path: Path | str, line_no: int | None = None, col: int | None = None) -> str:
    location = display_path(path)
    if line_no is not None:
        location = f"{location}:{line_no}"
    if col is not None:
        location = f"{location}:{col}"
    return location


@dataclass
class PathConfig:
    """Resolved paths for a given play."""

    play_name: str
    root: Path = ROOT
    build_root: Path = field(default_factory=lambda: ROOT.parent / "build")
    plays_dir: Path = field(default_factory=lambda: ROOT.parent / "plays")
    snippets_dir: Path = field(default_factory=lambda: ROOT.parent / "snippets")
    cache: Dict[Path, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.play_dir = self.plays_dir / self.play_name
        self.play_text = self.play_dir / "play.txt"
        self.production_markdown = self.play_dir / "production.md"
        self.build_dir = self.build_root / self.play_name
        self.logs_dir = self.build_root / "logs"
        self.paragraphs_path = self.build_dir / "paragraphs.txt"
        self.blocks_dir = self.build_dir / "blocks"
        self.roles_dir = self.build_dir / "roles"
        self.index_path = self.build_dir / "INDEX.files"
        self.audio_out_dir = self.build_dir / "audio"
        self.audio_play_dir = self.audio_out_dir / "play"
        self.segments_dir = self.audio_out_dir / "segments"
        self.markdown_dir = self.build_dir / "markdown"
        self.markdown_roles_dir = self.markdown_dir / "roles"
        self.recordings_dir = self.play_dir / "recordings"
        self.callouts_dir = self.play_dir / "callouts"
        self.general_snippets_dir = self.snippets_dir / "default_narrator"
        self.librivox_snippets_dir = self.general_snippets_dir / "librivox"
        self.target_dirs = [self.blocks_dir, self.roles_dir]
        self.extra_files = [self.paragraphs_path, self.index_path]

    def get_audio_length_ms(self, path: Path) -> int:
        """Return audio length in ms, caching results (0 if missing)."""
        from pydub import AudioSegment

        if path in self.cache:
            return self.cache[path]
        if not path.exists():
            raise RuntimeError(f"Audio file missing: {display_path(path)}")
        length = len(AudioSegment.from_file(path))
        self.cache[path] = length
        return length


_CURRENT: PathConfig | None = None


def set_play_name(play_name: str | None = None) -> PathConfig:
    """Update the current path config (legacy helper)."""
    global _CURRENT
    _CURRENT = PathConfig(play_name or default_play_name())
    return _CURRENT


def current() -> PathConfig:
    global _CURRENT
    if _CURRENT is None:
        _CURRENT = PathConfig(default_play_name())
    return _CURRENT


# Backwards-compatible aliases (avoid in new code)
_ALIASES = PathConfig(DEFAULT_PLAY_NAME)
DEFAULT_PLAY = _ALIASES.play_text
BUILD_DIR = _ALIASES.build_dir
PARAGRAPHS_PATH = _ALIASES.paragraphs_path
BLOCKS_DIR = _ALIASES.blocks_dir
ROLES_DIR = _ALIASES.roles_dir
INDEX_PATH = _ALIASES.index_path
AUDIO_OUT_DIR = _ALIASES.audio_out_dir
AUDIO_PLAY_DIR = _ALIASES.audio_play_dir
SEGMENTS_DIR = _ALIASES.segments_dir
RECORDINGS_DIR = _ALIASES.recordings_dir
CALLOUTS_DIR = _ALIASES.callouts_dir
MARKDOWN_DIR = _ALIASES.markdown_dir
MARKDOWN_ROLES_DIR = _ALIASES.markdown_roles_dir
SNIPPETS_DIR = _ALIASES.snippets_dir
GENERAL_SNIPPETS_DIR = _ALIASES.general_snippets_dir
LIBRIVOX_SNIPPETS_DIR = _ALIASES.librivox_snippets_dir
LOGS_DIR = _ALIASES.logs_dir
TARGET_DIRS = _ALIASES.target_dirs
EXTRA_FILES = _ALIASES.extra_files
