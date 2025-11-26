#!/usr/bin/env python3
"""Remove generated files in the blocks and parts folders."""
from paths import TARGET_DIRS, EXTRA_FILES


def main() -> None:
    for directory in TARGET_DIRS:
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if path.is_file():
                path.unlink()

    for file_path in EXTRA_FILES:
        if file_path.exists() and file_path.is_file():
            file_path.unlink()


if __name__ == "__main__":
    main()
