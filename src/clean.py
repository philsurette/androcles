#!/usr/bin/env python3
"""Remove generated files in the blocks and parts folders."""
import paths


def main(paths_config: paths.PathConfig | None = None) -> None:
    cfg = paths_config or paths.current()
    for directory in cfg.target_dirs:
        if not directory.exists():
            continue
        for path in directory.iterdir():
            if path.is_file():
                path.unlink()

    for file_path in cfg.extra_files:
        if file_path.exists() and file_path.is_file():
            file_path.unlink()


if __name__ == "__main__":
    main()
