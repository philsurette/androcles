from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict

from pydub import AudioSegment
from play_config import PlayConfig

ROOT = Path(__file__).resolve().parent
DEFAULT_PLAY_NAME = PlayConfig.load().play_id


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
        if path in self.cache:
            return self.cache[path]
        if not path.exists():
            raise RuntimeError(f"Audio file missing: {path}")
        length = len(AudioSegment.from_file(path))
        self.cache[path] = length
        return length


_CURRENT = PathConfig(DEFAULT_PLAY_NAME)


def set_play_name(play_name: str | None = None) -> PathConfig:
    """Update the current path config (legacy helper)."""
    global _CURRENT
    _CURRENT = PathConfig(play_name or DEFAULT_PLAY_NAME)
    return _CURRENT


def current() -> PathConfig:
    return _CURRENT


# Backwards-compatible aliases (avoid in new code)
DEFAULT_PLAY = _CURRENT.play_text
BUILD_DIR = _CURRENT.build_dir
PARAGRAPHS_PATH = _CURRENT.paragraphs_path
BLOCKS_DIR = _CURRENT.blocks_dir
ROLES_DIR = _CURRENT.roles_dir
INDEX_PATH = _CURRENT.index_path
AUDIO_OUT_DIR = _CURRENT.audio_out_dir
AUDIO_PLAY_DIR = _CURRENT.audio_play_dir
SEGMENTS_DIR = _CURRENT.segments_dir
RECORDINGS_DIR = _CURRENT.recordings_dir
CALLOUTS_DIR = _CURRENT.callouts_dir
MARKDOWN_DIR = _CURRENT.markdown_dir
MARKDOWN_ROLES_DIR = _CURRENT.markdown_roles_dir
SNIPPETS_DIR = _CURRENT.snippets_dir
GENERAL_SNIPPETS_DIR = _CURRENT.general_snippets_dir
LIBRIVOX_SNIPPETS_DIR = _CURRENT.librivox_snippets_dir
LOGS_DIR = _CURRENT.logs_dir
TARGET_DIRS = _CURRENT.target_dirs
EXTRA_FILES = _CURRENT.extra_files
