from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT.parent / "build"
PLAYS_DIR = ROOT.parent / "plays"
DEFAULT_PLAY = PLAYS_DIR / "androcles" / "play.txt"
PARAGRAPHS_PATH = BUILD_DIR / "paragraphs.txt"

# Output directories
BLOCKS_DIR = BUILD_DIR / "blocks"
ROLES_DIR = BUILD_DIR / "roles"
BLOCKS_EXT = ".blocks"
INDEX_PATH = BUILD_DIR / "INDEX.files"
AUDIO_OUT_DIR = BUILD_DIR / "audio"
RECORDINGS_DIR = DEFAULT_PLAY.parent / "recordings"
CALLOUTS_DIR = DEFAULT_PLAY.parent / "callouts"

# Clean targets
TARGET_DIRS = [BLOCKS_DIR, ROLES_DIR]
EXTRA_FILES = [PARAGRAPHS_PATH, INDEX_PATH]
