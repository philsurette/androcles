from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT.parent / "build"

PARAGRAPHS_PATH = BUILD_DIR / "paragraphs.txt"
SRC_PATH = ROOT / "src.txt"

# Output directories
BLOCKS_DIR = BUILD_DIR / "blocks"
ROLES_DIR = BUILD_DIR / "roles"
BLOCKS_EXT = ".blocks"

# Clean targets
TARGET_DIRS = [BLOCKS_DIR, ROLES_DIR]
EXTRA_FILES = [PARAGRAPHS_PATH]
