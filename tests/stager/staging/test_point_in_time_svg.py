from __future__ import annotations

import json
from pathlib import Path

from stager.staging.parser import StagingParser
from stager.staging.resolver import StagingResolver
from stager.staging.svg_renderer import StageSvgRenderer


def test_parser_accepts_text_only_stage_and_scene_snapshot() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9
anchor door_l = UL
anchor table = C

scene 1.2 snapshot
HAM @ DL face=CLA
CLA @ UC
OPH offstage via=door_l
table @ C
sword @ table
"""
    )

    assert document.stage.stage_type == "proscenium"
    assert document.stage.measured is False
    assert document.anchors["door_l"].at.source == "UL"
    assert document.snapshots["1.2"].placements[0].entity == "HAM"
    assert document.snapshots["1.2"].placements[2].offstage is True


def test_resolver_uses_default_stage_and_preserves_unknowns_as_diagnostics() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9

scene 1.2 snapshot
HAM @ DL
CLA @ nowhere
"""
    )

    snapshot = StagingResolver().resolve_snapshot(document, "1.2")

    ham = next(placement for placement in snapshot.placements if placement.entity == "HAM")
    cla = next(placement for placement in snapshot.placements if placement.entity == "CLA")
    assert ham.point is not None
    assert ham.point.x < 0
    assert cla.point is None
    assert any("nowhere" in diagnostic.message for diagnostic in snapshot.diagnostics)


def test_resolver_supports_measured_stage_and_elevated_locations() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium width=40 depth=30 units=ft
grid standard=9
anchor balcony_l at=(-8,24,8)

scene 2 snapshot
HAM @ balcony_l
"""
    )

    snapshot = StagingResolver().resolve_snapshot(document, "2")

    ham = snapshot.placements[0]
    assert snapshot.stage.measured is True
    assert ham.point is not None
    assert ham.point.z == 8


def test_svg_renderer_outputs_stage_grid_actor_and_diagnostics() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9
anchor table = C

scene 1.2 snapshot
HAM @ DL face=house
OPH offstage via=door_l
sword @ table
CLA @ nowhere
"""
    )
    snapshot = StagingResolver().resolve_snapshot(document, "1.2")

    svg = StageSvgRenderer().render(snapshot)

    assert svg.startswith("<?xml")
    assert "<svg" in svg
    assert "HAM" in svg
    assert "face house" in svg
    assert "sword" in svg
    assert "Offstage / unknown" in svg
    assert "nowhere" in svg


def test_render_point_cli_writes_svg_and_json(tmp_path: Path) -> None:
    source = tmp_path / "stage.txt"
    svg_path = tmp_path / "stage.svg"
    json_path = tmp_path / "stage.json"
    source.write_text(
        """
stage type=proscenium
grid standard=9
anchor door_l = UL

scene 1.2 snapshot
HAM @ DL
OPH offstage via=door_l
""",
        encoding="utf-8",
    )

    from stager.staging.render_point import main
    import sys

    original_argv = sys.argv
    try:
        sys.argv = [
            "render_point",
            str(source),
            "--scene",
            "1.2",
            "--out",
            str(svg_path),
            "--json-out",
            str(json_path),
        ]
        main()
    finally:
        sys.argv = original_argv

    assert "HAM" in svg_path.read_text(encoding="utf-8")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["scene_id"] == "1.2"
