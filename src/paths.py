from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT.parent / "build"
PLAYS_DIR = ROOT.parent / "plays"

PARAGRAPHS_PATH = BUILD_DIR / "paragraphs.txt"
DEFAULT_PLAY = PLAYS_DIR / "androcles.txt"

# Output directories
BLOCKS_DIR = BUILD_DIR / "blocks"
ROLES_DIR = BUILD_DIR / "roles"
BLOCKS_EXT = ".blocks"

# Clean targets
TARGET_DIRS = [BLOCKS_DIR, ROLES_DIR]
EXTRA_FILES = [PARAGRAPHS_PATH]
