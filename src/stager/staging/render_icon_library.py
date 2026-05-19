from __future__ import annotations

import argparse
from pathlib import Path

from stager.shared import paths
from stager.staging.svg_icons import StageSvgIconLibrary


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the staging SVG icon library as a browsable contact sheet.")
    parser.add_argument("--out", required=True, help="Output SVG path.")
    args = parser.parse_args()

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(StageSvgIconLibrary().catalog_svg(), encoding="utf-8")
    print(paths.display_path(output_path))


if __name__ == "__main__":
    main()
