from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT.parent / "build"
LOGS_DIR = BUILD_DIR / "logs"
PLAYS_DIR = ROOT.parent / "plays"
DEFAULT_PLAY = PLAYS_DIR / "androcles" / "play.txt"
PARAGRAPHS_PATH = BUILD_DIR / "paragraphs.txt"

# Output directories
BLOCKS_DIR = BUILD_DIR / "blocks"
ROLES_DIR = BUILD_DIR / "roles"
BLOCKS_EXT = ".blocks"
INDEX_PATH = BUILD_DIR / "INDEX.files"
AUDIO_OUT_DIR = BUILD_DIR / "audio"
AUDIO_PLAY_DIR = AUDIO_OUT_DIR / "play"
SEGMENTS_DIR = AUDIO_OUT_DIR / "segments"
RECORDINGS_DIR = DEFAULT_PLAY.parent / "recordings"
CALLOUTS_DIR = DEFAULT_PLAY.parent / "callouts"
MARKDOWN_DIR = BUILD_DIR / "markdown"
MARKDOWN_ROLES_DIR = MARKDOWN_DIR / "roles"

# Clean targets
TARGET_DIRS = [BLOCKS_DIR, ROLES_DIR]
EXTRA_FILES = [PARAGRAPHS_PATH, INDEX_PATH]
