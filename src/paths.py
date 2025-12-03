from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUILD_ROOT = ROOT.parent / "build"
LOGS_DIR = BUILD_ROOT / "logs"
PLAYS_DIR = ROOT.parent / "plays"
DEFAULT_PLAY_NAME = "androcles"
PLAY_NAME = DEFAULT_PLAY_NAME

# Populated by set_play_name
DEFAULT_PLAY: Path
BUILD_DIR: Path
PARAGRAPHS_PATH: Path

# Output directories
BLOCKS_DIR: Path
ROLES_DIR: Path
BLOCKS_EXT = ".blocks"
INDEX_PATH: Path
AUDIO_OUT_DIR: Path
AUDIO_PLAY_DIR: Path
SEGMENTS_DIR: Path
RECORDINGS_DIR: Path
CALLOUTS_DIR: Path
MARKDOWN_DIR: Path
MARKDOWN_ROLES_DIR: Path

# Clean targets
TARGET_DIRS: list[Path]
EXTRA_FILES: list[Path]


def set_play_name(play_name: str | None = None) -> Path:
    """
    Configure the active play name and update dependent paths under build/<play>.
    Returns the resolved play text path.
    """
    global PLAY_NAME, DEFAULT_PLAY, BUILD_DIR, PARAGRAPHS_PATH
    global BLOCKS_DIR, ROLES_DIR, INDEX_PATH, AUDIO_OUT_DIR, AUDIO_PLAY_DIR, SEGMENTS_DIR
    global RECORDINGS_DIR, CALLOUTS_DIR, MARKDOWN_DIR, MARKDOWN_ROLES_DIR
    global TARGET_DIRS, EXTRA_FILES

    PLAY_NAME = play_name or DEFAULT_PLAY_NAME
    DEFAULT_PLAY = PLAYS_DIR / PLAY_NAME / "play.txt"
    BUILD_DIR = BUILD_ROOT / PLAY_NAME
    PARAGRAPHS_PATH = BUILD_DIR / "paragraphs.txt"
    BLOCKS_DIR = BUILD_DIR / "blocks"
    ROLES_DIR = BUILD_DIR / "roles"
    INDEX_PATH = BUILD_DIR / "INDEX.files"
    AUDIO_OUT_DIR = BUILD_DIR / "audio"
    AUDIO_PLAY_DIR = AUDIO_OUT_DIR / "play"
    SEGMENTS_DIR = AUDIO_OUT_DIR / "segments"
    MARKDOWN_DIR = BUILD_DIR / "markdown"
    MARKDOWN_ROLES_DIR = MARKDOWN_DIR / "roles"
    RECORDINGS_DIR = DEFAULT_PLAY.parent / "recordings"
    CALLOUTS_DIR = DEFAULT_PLAY.parent / "callouts"
    TARGET_DIRS = [BLOCKS_DIR, ROLES_DIR]
    EXTRA_FILES = [PARAGRAPHS_PATH, INDEX_PATH]
    return DEFAULT_PLAY


# Initialize module globals with the default play.
set_play_name(DEFAULT_PLAY_NAME)
