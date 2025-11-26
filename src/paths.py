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

# Clean targets
TARGET_DIRS = [BLOCKS_DIR, ROLES_DIR]
EXTRA_FILES = [PARAGRAPHS_PATH, INDEX_PATH]
