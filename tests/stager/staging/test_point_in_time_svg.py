from __future__ import annotations

import json
import re
from pathlib import Path

from stager.staging.parser import StagingParser
from stager.staging.resolver import StagingResolver
from stager.staging.state_resolver import StagingStateResolver
from stager.staging.svg_icons import StageSvgIconLibrary
from stager.staging.svg_renderer import StageSvgRenderer


def test_parser_accepts_text_only_stage_and_scene_snapshot() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9
actor HAM label=HM name=Hamlet
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
    assert document.actors["HAM"].label == "HM"
    assert document.actors["HAM"].name == "Hamlet"
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


def test_resolver_and_renderer_support_elevated_connectors_and_diagnostics() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium width=40 depth=30 units=ft
grid standard=9
level deck z=0
level balcony z=8
anchor deck_l at=(-12,14,0)
anchor balcony_l at=(-8,24,8)
stair stair_l from=deck_l to=balcony_l
ramp bad_ramp from=nowhere to=balcony_l

scene 2 snapshot
HAM @ balcony_l
"""
    )

    snapshot = StagingResolver().resolve_snapshot(document, "2")
    svg = StageSvgRenderer(orientation="landscape").render(snapshot)

    assert snapshot.connectors["stair_l"].start.point is not None
    assert snapshot.connectors["stair_l"].end.point is not None
    assert snapshot.connectors["stair_l"].end.point.z == 8
    assert "Unresolved connector start 'nowhere' for bad_ramp" in [diagnostic.message for diagnostic in snapshot.diagnostics]
    assert '<line class="connector"' in svg
    assert "<title>stair_l stair</title>" in svg
    assert ">stair 0->8</text>" in svg


def test_renderer_draws_level_surfaces_with_elevation_labels() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium width=40 depth=30 units=ft
grid standard=9
level balcony at=UC size=(18,4) z=8

scene 2 snapshot
HAM @ UC
"""
    )

    snapshot = StagingResolver().resolve_snapshot(document, "2")
    svg = StageSvgRenderer(orientation="landscape").render(snapshot)

    assert snapshot.levels["balcony"].at is not None
    assert snapshot.levels["balcony"].at.point is not None
    assert '<rect class="level-surface"' in svg
    assert "<title>balcony +8</title>" in svg
    assert ">balcony +8</text>" in svg


def test_renderer_colors_actors_and_objects_by_elevation() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium width=40 depth=30 units=ft
grid standard=9
actor HAM label=HM name=Hamlet
actor CLA label=CD name=Claudius
level balcony at=UC size=(18,4) z=8
anchor balcony_l at=(-8,24,8)
anchor deck_c at=(0,8,0)

scene 2 snapshot
HAM @ balcony_l
CLA @ deck_c
flower @ balcony_l
book @ deck_c
"""
    )

    snapshot = StagingResolver().resolve_snapshot(document, "2")
    svg = StageSvgRenderer(orientation="landscape").render(snapshot)

    assert 'class="actor-circle" cx="232" cy="136" r="13" style="fill:#d9edf7;stroke:#2f6f9f"' in svg
    assert 'class="actor-circle" cx="360" cy="392" r="13" style="fill:#e6e6e6;stroke:#555555"' in svg
    assert '<g><title>flower</title><use class="stage-icon icon-prop" href="#stage-icon-flower" style="color:#2f6f9f"' in svg
    assert '<g><title>book</title><use class="stage-icon icon-prop" href="#stage-icon-book" style="color:#555555"' in svg


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


def test_state_resolver_applies_ordered_blocking_beats() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9
actor HAM label=HM name=Hamlet
actor CLA label=CD name=Claudius
actor OPH label=OP name=Ophelia
set table kind=furniture at=C size=(5,3)

scene 1.2 snapshot
HAM @ DL face=CLA
CLA @ UC
OPH offstage via=door_l
sword @ table

beat b1 scene=1.2
HAM move DL -> C face=CLA
OPH enter door_l -> DR

beat b2 scene=1.2
CLA -> DC
sword remove
"""
    )

    snapshot = StagingStateResolver().resolve_beat(document, "1.2", "b2")

    placements = {placement.entity: placement for placement in snapshot.placements}
    assert snapshot.scene_id == "1.2@b2"
    assert placements["HAM"].source == "C"
    assert placements["OPH"].source == "DR"
    assert placements["CLA"].source == "DC"
    assert placements["sword"].offstage is True
    assert placements["HAM"].point is not None
    assert placements["HAM"].point.x == 0


def test_state_resolver_warns_for_unknown_beat() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9

scene 1.2 snapshot
HAM @ DL
"""
    )

    snapshot = StagingStateResolver().resolve_beat(document, "1.2", "missing")

    assert any("Unknown beat 'missing' for scene '1.2'" == diagnostic.message for diagnostic in snapshot.diagnostics)


def test_svg_renderer_uses_layers_top_left_area_labels_and_offsets_actor_collisions() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9
set table kind=furniture at=C size=(5,3)
actor HAM label=HM name=Hamlet
actor CLA label=CD name=Claudius

scene 1.2 snapshot
HAM @ C
CLA @ C
sword @ table
dagger @ table
"""
    )
    snapshot = StagingResolver().resolve_snapshot(document, "1.2")

    svg = StageSvgRenderer().render(snapshot)

    assert '<g class="layer-props">' in svg
    assert '<g class="layer-actors">' in svg
    assert ".area-label{font:12px sans-serif;fill:#555;text-anchor:start}" in svg
    assert '<text class="area-label" x="45" y="55">UL</text>' in svg
    assert ".actor-circle{fill-opacity:.86;stroke-width:1.5}" in svg
    actor_circles = re.findall(r'<circle class="actor-circle" cx="([^"]+)" cy="([^"]+)"', svg)
    assert len(actor_circles) == 2
    assert actor_circles[0] != actor_circles[1]
    assert "<title>Hamlet</title>" in svg
    assert ">HM</text>" in svg
    assert "<title>Claudius</title>" in svg
    assert ">CD</text>" in svg
    prop_labels = re.findall(r'<use class="stage-icon icon-prop" href="#stage-icon-[^"]+"[^>]* x="([^"]+)" y="([^"]+)"', svg)
    assert len(prop_labels) == 2
    assert prop_labels[0] != prop_labels[1]
    assert svg.index('<g class="layer-props">') < svg.index('<g class="layer-actors">')
    assert 'href="#stage-icon-sword"' in svg
    assert 'href="#stage-icon-dagger"' in svg
    assert "<title>sword</title>" in svg
    assert "<title>dagger</title>" in svg
    assert ">sword</text>" not in svg
    assert ">dagger</text>" not in svg


def test_svg_renderer_uses_snapshot_position_for_placed_set_piece() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9
set table kind=furniture at=C size=(5,3)

scene 1.2 snapshot
table @ DL
"""
    )
    snapshot = StagingResolver().resolve_snapshot(document, "1.2")

    svg = StageSvgRenderer().render(snapshot)

    assert svg.count('href="#stage-icon-table"') == 1
    assert "<title>table</title>" in svg
    assert ">table</text>" not in svg
    assert svg.index('<g class="layer-scenery">') < svg.index('href="#stage-icon-table"') < svg.index('<g class="layer-props">')


def test_svg_renderer_defaults_to_portrait_with_downstage_on_right() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9
actor HAM label=HM name=Hamlet

scene 1.2 snapshot
HAM @ DL
"""
    )
    snapshot = StagingResolver().resolve_snapshot(document, "1.2")

    svg = StageSvgRenderer().render(snapshot)

    assert '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="1260"' in svg
    match = re.search(r'<circle class="actor-circle" cx="([^"]+)" cy="([^"]+)"', svg)
    assert match is not None
    assert float(match.group(1)) > 450
    assert float(match.group(2)) < 300


def test_svg_renderer_supports_landscape_orientation() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9
actor HAM label=HM name=Hamlet

scene 1.2 snapshot
HAM @ DL
"""
    )
    snapshot = StagingResolver().resolve_snapshot(document, "1.2")

    svg = StageSvgRenderer(orientation="landscape").render(snapshot)

    assert '<svg xmlns="http://www.w3.org/2000/svg" width="940" height="506"' in svg
    match = re.search(r'<circle class="actor-circle" cx="([^"]+)" cy="([^"]+)"', svg)
    assert match is not None
    assert float(match.group(1)) < 250
    assert float(match.group(2)) > 350


def test_svg_icon_library_contains_stage_object_icons() -> None:
    icons = StageSvgIconLibrary()
    expected_icons = [
        "actor",
        "actor-group",
        "chair",
        "stool",
        "bench",
        "sofa",
        "table",
        "small-table",
        "desk",
        "bed",
        "cabinet",
        "chest",
        "crate",
        "screen",
        "piano",
        "music-stand",
        "prop",
        "basket",
        "bag",
        "box",
        "letter",
        "book",
        "newspaper",
        "key",
        "lantern",
        "candle",
        "lamp",
        "umbrella",
        "cane",
        "rope",
        "bell",
        "mask",
        "cloth",
        "flag",
        "flower",
        "cup",
        "bottle",
        "tray",
        "food",
        "sword",
        "dagger",
        "staff",
        "shield",
        "pistol",
        "rifle",
        "hat",
        "crown",
        "cloak",
        "telephone",
        "radio",
        "instrument",
        "practical-light",
        "smoke-source",
        "puppet",
        "dummy",
        "animal",
        "spike-mark",
        "handoff",
        "cue-point",
        "hazard",
        "preset",
        "strike",
        "storage",
    ]

    assert all(icons.has_icon(icon) for icon in expected_icons)


def test_svg_icon_library_renders_browsable_catalog() -> None:
    svg = StageSvgIconLibrary().catalog_svg(columns=4)

    assert svg.startswith("<?xml")
    assert '<symbol id="stage-icon-chair"' in svg
    assert '<use class="icon" href="#stage-icon-chair"' in svg
    assert '<text class="label"' in svg


def test_render_icon_library_cli_writes_svg(tmp_path: Path) -> None:
    output_path = tmp_path / "icons.svg"

    from stager.staging.render_icon_library import main
    import sys

    original_argv = sys.argv
    try:
        sys.argv = ["render_icon_library", "--out", str(output_path)]
        main()
    finally:
        sys.argv = original_argv

    assert '<symbol id="stage-icon-table"' in output_path.read_text(encoding="utf-8")


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
            "--orientation",
            "landscape",
        ]
        main()
    finally:
        sys.argv = original_argv

    assert "HAM" in svg_path.read_text(encoding="utf-8")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["scene_id"] == "1.2"


def test_render_point_cli_writes_beat_state(tmp_path: Path) -> None:
    source = tmp_path / "stage.txt"
    svg_path = tmp_path / "stage.svg"
    json_path = tmp_path / "stage.json"
    source.write_text(
        """
stage type=proscenium
grid standard=9
actor HAM label=HM name=Hamlet

scene 1.2 snapshot
HAM @ DL

beat b1 scene=1.2
HAM -> C
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
            "--beat",
            "b1",
            "--out",
            str(svg_path),
            "--json-out",
            str(json_path),
        ]
        main()
    finally:
        sys.argv = original_argv

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["scene_id"] == "1.2@b1"
    assert data["placements"][0]["source"] == "C"
