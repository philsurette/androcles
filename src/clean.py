#!/usr/bin/env python3
"""Remove generated files in the blocks and parts folders."""
import paths


def main() -> None:
    for directory in paths.TARGET_DIRS:
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if path.is_file():
                path.unlink()

    for file_path in paths.EXTRA_FILES:
        if file_path.exists() and file_path.is_file():
            file_path.unlink()


if __name__ == "__main__":
    main()
