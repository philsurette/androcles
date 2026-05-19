from __future__ import annotations

import json
import re
from pathlib import Path

from stager.staging.diagram_state_builder import DiagramStateBuilder
from stager.staging.parser import StagingParser
from stager.staging.export_service import StagingExportService
from stager.staging.production_exporter import ProductionStagingExporter
from stager.staging.resolver import StagingResolver
from stager.staging.state_resolver import StagingStateResolver
from stager.staging.svg_icons import StageSvgIconLibrary
from stager.staging.svg_renderer import StageSvgRenderer
from stager.scriptwright.production_script_parser import ProductionScriptParser
from stager.shared import paths


def render_svg(snapshot, orientation: str = "portrait") -> str:
    return StageSvgRenderer(orientation=orientation).render(DiagramStateBuilder().build(snapshot))


def test_production_staging_exporter_writes_ordered_scene_sections_and_anchored_beats() -> None:
    production = ProductionScriptParser().parse_text(
        """
// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# 1-0 ACT I
1.2-1 @description: A room.
/*: stage type=proscenium
/*: grid standard=9
/*: setup act1
/*: piece table kind=table at=C size=(5,3)
/*: scene 1.2 set=act1
/HM: @ DL face=CD
/CD: @ UC
/OP: offstage via=door_l
/HM: move DL -> C face=CD
1.2-2 HM: I move.
/CD: move UC -> DR
1.2-3 CD: I move.
"""
    )

    exported = ProductionStagingExporter().export(production)

    assert "scene 1.2 set=act1\nHM @ DL face=CD\nCD @ UC\nOP offstage via=door_l" in exported
    assert "b1 @ 1.2-2\nHM move DL -> C face=CD" in exported
    assert "b2 @ 1.2-3\nCD move UC -> DR" in exported


def test_staging_export_service_writes_build_artifact(tmp_path: Path) -> None:
    cfg = paths.PathConfig(
        play_name="hamlet",
        root=tmp_path / "src",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )
    cfg.play_dir.mkdir(parents=True)
    cfg.production_markdown.write_text(
        """
// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# 1-0 ACT I
1.2-1 @description: A room.
/*: stage type=proscenium
/*: scene 1.2 set=act1
/HM: @ DL
1.2-2 HM: Speak.
""",
        encoding="utf-8",
    )

    result = StagingExportService(paths_config=cfg).export()

    assert result.written is True
    assert result.output_path == cfg.build_dir / "staging" / "staging.txt"
    assert "scene 1.2 set=act1\nHM @ DL" in result.output_path.read_text(encoding="utf-8")


def test_staging_export_service_removes_stale_artifact_when_no_staging_notes(tmp_path: Path) -> None:
    cfg = paths.PathConfig(
        play_name="hamlet",
        root=tmp_path / "src",
        build_root=tmp_path / "build",
        plays_dir=tmp_path / "plays",
        snippets_dir=tmp_path / "snippets",
    )
    cfg.play_dir.mkdir(parents=True)
    stale_path = cfg.build_dir / "staging" / "staging.txt"
    stale_path.parent.mkdir(parents=True)
    stale_path.write_text("stale\n", encoding="utf-8")
    cfg.production_markdown.write_text(
        """
// script_format: quince-production-v1
// source_kind: production
// production_ids: locked

# 1-0 ACT I
1.2-1 HM: Speak.
""",
        encoding="utf-8",
    )

    result = StagingExportService(paths_config=cfg).export()

    assert result.written is False
    assert result.removed_stale is True
    assert not stale_path.exists()


def test_parser_accepts_text_only_stage_and_scene_snapshot() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9
actor HM name=Hamlet
anchor door_l = UL
anchor table = C

scene 1.2
HM @ DL face=CD
CD @ UC
OP offstage via=door_l
table @ C
sword @ table
"""
    )

    assert document.stage.stage_type == "proscenium"
    assert document.stage.measured is False
    assert document.actors["HM"].label == "HM"
    assert document.actors["HM"].name == "Hamlet"
    assert document.anchors["door_l"].at.source == "UL"
    assert document.snapshots["1.2"].placements[0].entity == "HM"
    assert document.snapshots["1.2"].placements[2].offstage is True


def test_parser_and_resolver_support_named_sets_for_scene_snapshots() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9
actor HM name=Hamlet

setup act1
level balcony at=UC size=(18,4) z=8
anchor balcony_l at=(-8,20,8)
piece table kind=table at=C size=(5,3)

setup act2
anchor throne = UC
piece bench kind=bench at=DR size=(5,2)

scene 1.2 set=act1
HM @ balcony_l
sword @ table

scene 2.1 set=act2
HM @ throne
"""
    )

    act1 = StagingResolver().resolve_snapshot(document, "1.2")
    act2 = StagingResolver().resolve_snapshot(document, "2.1")

    assert document.snapshots["1.2"].set_id == "act1"
    assert document.snapshots["2.1"].set_id == "act2"
    assert "balcony" in act1.levels
    assert "bench" not in act1.set_pieces
    assert "bench" in act2.set_pieces
    assert act1.placements[0].point is not None
    assert act1.placements[0].point.z == 8
    assert act2.placements[0].source == "throne"


def test_diagram_state_builder_outputs_renderer_contract() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9
actor HM name=Hamlet
actor CD name=Claudius

setup act1
piece table kind=table at=C size=(5,3)

scene 1.2 set=act1
HM @ C
CD @ C
sword @ table
dagger @ table
OP offstage via=door_l
"""
    )

    snapshot = StagingResolver().resolve_snapshot(document, "1.2")
    diagram = DiagramStateBuilder().build(snapshot)
    data = diagram.to_dict()

    assert data["format"] == "quince.blocking.diagram_state"
    assert data["format_version"] == "1.0"
    assert data["diagram_id"] == "scene:1.2"
    assert data["diagram_kind"] == "scene"
    assert data["set_id"] == "act1"
    assert any(entity["id"] == "actor:HM" and entity["label"] == "HM" for entity in data["entities"])
    assert any(entity["id"] == "prop:sword" and entity["icon"] == "sword" and entity["slot_index"] == 0 for entity in data["entities"])
    assert any(entity["id"] == "prop:dagger" and entity["slot_index"] == 1 for entity in data["entities"])
    assert any(entity["id"] == "actor:CD" and entity["offset"]["x"] == 18.0 for entity in data["entities"])
    assert data["offstage"][0]["id"] == "actor:OP"


def test_resolver_uses_default_stage_and_preserves_unknowns_as_diagnostics() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9

scene 1.2
HM @ DL
CD @ nowhere
"""
    )

    snapshot = StagingResolver().resolve_snapshot(document, "1.2")

    ham = next(placement for placement in snapshot.placements if placement.entity == "HM")
    cla = next(placement for placement in snapshot.placements if placement.entity == "CD")
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

scene 2
HM @ balcony_l
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

scene 2
HM @ balcony_l
"""
    )

    snapshot = StagingResolver().resolve_snapshot(document, "2")
    svg = render_svg(snapshot, orientation="landscape")

    assert snapshot.connectors["stair_l"].start.point is not None
    assert snapshot.connectors["stair_l"].end.point is not None
    assert snapshot.connectors["stair_l"].end.point.z == 8
    assert "Unresolved connector start 'nowhere' for bad_ramp" in [diagnostic.message for diagnostic in snapshot.diagnostics]
    assert '<line class="stair-tread"' in svg
    assert '<polygon class="stair-footprint"' in svg
    assert '<line class="connector"' not in svg
    assert "<title>stair_l stair</title>" in svg
    assert ">stair 0->8</text>" in svg
    assert 'stroke="#555555"' in svg


def test_renderer_draws_level_surfaces_with_elevation_labels() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium width=40 depth=30 units=ft
grid standard=9
level balcony at=UC size=(18,4) z=8

scene 2
HM @ UC
"""
    )

    snapshot = StagingResolver().resolve_snapshot(document, "2")
    svg = render_svg(snapshot, orientation="landscape")

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
actor HM name=Hamlet
actor CD name=Claudius
level balcony at=UC size=(18,4) z=8
anchor balcony_l at=(-8,24,8)
anchor deck_c at=(0,8,0)

scene 2
HM @ balcony_l
CD @ deck_c
flower @ balcony_l
book @ deck_c
"""
    )

    snapshot = StagingResolver().resolve_snapshot(document, "2")
    svg = render_svg(snapshot, orientation="landscape")

    assert 'class="actor-circle" cx="232" cy="136" r="13" style="fill:#d9edf7;stroke:#2f6f9f"' in svg
    assert 'class="actor-circle" cx="360" cy="392" r="13" style="fill:#e6e6e6;stroke:#555555"' in svg
    assert '<g><title>flower</title><use class="stage-icon icon-prop" href="#stage-icon-flower" style="color:#2f6f9f"' in svg
    assert 'class="actor-circle" cx="360" cy="392" r="13" style="fill:#e6e6e6;stroke:#555555"' in svg


def test_svg_renderer_outputs_stage_grid_actor_and_diagnostics() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9
anchor table = C

scene 1.2
HM @ DL face=house
OP offstage via=door_l
sword @ table
CD @ nowhere
"""
    )
    snapshot = StagingResolver().resolve_snapshot(document, "1.2")

    svg = render_svg(snapshot)

    assert svg.startswith("<?xml")
    assert "<svg" in svg
    assert "HM" in svg
    assert "face house" in svg
    assert "sword" in svg
    assert "Offstage / unknown" in svg
    assert "nowhere" in svg


def test_state_resolver_applies_ordered_blocking_beats() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9
actor HM name=Hamlet
actor CD name=Claudius
actor OP name=Ophelia
set table kind=furniture at=C size=(5,3)

scene 1.2
HM @ DL face=CD
CD @ UC
OP offstage via=door_l
sword @ table

b1 @ 1.2-2
HM move DL -> C face=CD
OP enter door_l -> DR

b2 @ 1.2-3
CD -> DC
sword remove
"""
    )

    snapshot = StagingStateResolver().resolve_beat(document, "1.2", "b2")

    placements = {placement.entity: placement for placement in snapshot.placements}
    assert snapshot.scene_id == "1.2@b2"
    assert placements["HM"].source == "C"
    assert placements["OP"].source == "DR"
    assert placements["CD"].source == "DC"
    assert placements["sword"].offstage is True
    assert placements["HM"].point is not None
    assert placements["HM"].point.x == 0
    assert placements["HM"].origin_point is None
    assert placements["OP"].origin_point is None
    assert placements["CD"].origin_source == "UC"

    previous = StagingStateResolver().resolve_beat(document, "1.2", "b1")
    previous_placements = {placement.entity: placement for placement in previous.placements}
    assert previous_placements["HM"].origin_source == "DL"
    assert previous_placements["OP"].origin_point is None
    assert previous_placements["CD"].next_source == "DC"
    assert previous_placements["HM"].next_point is None


def test_snapshot_resolver_keeps_latest_repeated_entity_placement() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9
actor LI name=Lillian

scene P
LI @ DL
LI @ DR face=CHRISTINE
"""
    )

    snapshot = StagingResolver().resolve_snapshot(document, "P")

    placements = [placement for placement in snapshot.placements if placement.entity == "LI"]
    assert len(placements) == 1
    assert placements[0].source == "DR"
    assert placements[0].face == "CHRISTINE"


def test_state_resolver_warns_for_unknown_beat() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9

scene 1.2
HM @ DL
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
actor HM name=Hamlet
actor CD name=Claudius

scene 1.2
HM @ C
CD @ C
sword @ table
dagger @ table
"""
    )
    snapshot = StagingResolver().resolve_snapshot(document, "1.2")

    svg = render_svg(snapshot)

    assert '<g class="layer-props">' in svg
    assert '<g class="layer-actors">' in svg
    assert ".area-label{font:12px sans-serif;fill:#555;text-anchor:start}" in svg
    assert '<text class="area-label" x="45" y="55">UL</text>' in svg
    assert ".actor-circle{fill-opacity:.86;stroke-width:1.5}" in svg
    assert ".actor-label{font:10px sans-serif;font-weight:700;fill:#111;" in svg
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

scene 1.2
table @ DL
"""
    )
    snapshot = StagingResolver().resolve_snapshot(document, "1.2")

    svg = render_svg(snapshot)

    assert svg.count('href="#stage-icon-table"') == 1
    assert "<title>table</title>" in svg
    assert ">table</text>" not in svg
    footprint = re.search(
        r'<rect class="set-piece-footprint" x="([^"]+)" y="([^"]+)"[\s\S]*?<g><title>table</title><use class="stage-icon icon-set-piece"[^>]* x="([^"]+)" y="([^"]+)"',
        svg,
    )
    assert footprint is not None
    assert float(footprint.group(3)) > float(footprint.group(1))
    assert float(footprint.group(4)) > float(footprint.group(2))
    assert float(footprint.group(3)) - float(footprint.group(1)) < 10
    assert float(footprint.group(4)) - float(footprint.group(2)) < 10
    assert svg.index('<g class="layer-scenery">') < svg.index('href="#stage-icon-table"') < svg.index('<g class="layer-props">')


def test_svg_renderer_defaults_to_portrait_with_downstage_on_right() -> None:
    document = StagingParser().parse(
        """
stage type=proscenium
grid standard=9
actor HM name=Hamlet

scene 1.2
HM @ DL
"""
    )
    snapshot = StagingResolver().resolve_snapshot(document, "1.2")

    svg = render_svg(snapshot)

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
actor HM name=Hamlet

scene 1.2
HM @ DL
"""
    )
    snapshot = StagingResolver().resolve_snapshot(document, "1.2")

    svg = render_svg(snapshot, orientation="landscape")

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
    source = tmp_path / "staging.txt"
    svg_path = tmp_path / "stage.svg"
    json_path = tmp_path / "stage.json"
    source.write_text(
        """
stage type=proscenium
grid standard=9
anchor door_l = UL

scene 1.2
HM @ DL
OP offstage via=door_l
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

    assert "HM" in svg_path.read_text(encoding="utf-8")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["scene_id"] == "1.2"


def test_render_point_cli_writes_beat_state(tmp_path: Path) -> None:
    source = tmp_path / "staging.txt"
    svg_path = tmp_path / "stage.svg"
    json_path = tmp_path / "stage.json"
    source.write_text(
        """
stage type=proscenium
grid standard=9
actor HM name=Hamlet

scene 1.2
HM @ DL

b1 @ 1.2-2
HM -> C
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
    assert data["format"] == "quince.blocking.diagram_state"
    assert data["diagram_kind"] == "beat"
    assert data["scene_id"] == "1.2"
    assert data["beat_id"] == "b1"
    assert data["entities"][0]["source"] == "C"
    assert data["entities"][0]["movement_from_source"] == "DL"


def test_block_cli_renders_beat_state_and_icons(tmp_path: Path) -> None:
    source = tmp_path / "staging.txt"
    svg_path = tmp_path / "stage.svg"
    scene_svg_path = tmp_path / "scene.svg"
    beat_svg_path = tmp_path / "beat.svg"
    icons_path = tmp_path / "icons.svg"
    source.write_text(
        """
stage type=proscenium
grid standard=9
actor HM name=Hamlet

scene 1.2
HM @ DL

b1 @ 1.2-2
HM -> C
""",
        encoding="utf-8",
    )

    from stager.staging.block import main
    import sys

    original_argv = sys.argv
    try:
        sys.argv = [
            "block",
            "render",
            str(source),
            "--scene",
            "1.2",
            "--beat",
            "b1",
            "--out",
            str(svg_path),
        ]
        main()
        sys.argv = [
            "block",
            "scene",
            str(source),
            "--scene",
            "1.2",
            "--out",
            str(scene_svg_path),
        ]
        main()
        sys.argv = [
            "block",
            "beat",
            str(source),
            "--scene",
            "1.2",
            "--beat",
            "b1",
            "--out",
            str(beat_svg_path),
        ]
        main()
        sys.argv = ["block", "icons", "--out", str(icons_path)]
        main()
    finally:
        sys.argv = original_argv

    assert "Scene 1.2@b1" in svg_path.read_text(encoding="utf-8")
    assert '<line class="movement-arrow"' in beat_svg_path.read_text(encoding="utf-8")
    assert "Scene 1.2" in scene_svg_path.read_text(encoding="utf-8")
    assert "Scene 1.2@b1" in beat_svg_path.read_text(encoding="utf-8")
    assert '<symbol id="stage-icon-table"' in icons_path.read_text(encoding="utf-8")


def test_block_cli_renders_stage_only_diagram(tmp_path: Path) -> None:
    source = tmp_path / "staging.txt"
    svg_path = tmp_path / "stage.svg"
    set_svg_path = tmp_path / "set.svg"
    json_path = tmp_path / "stage.json"
    set_json_path = tmp_path / "set.json"
    source.write_text(
        """
stage type=proscenium
grid standard=9
setup act1
level balcony at=UC size=(18,4) z=8
anchor door_l = UL
anchor deck_l at=CL
anchor balcony_l at=(-8,20,8)
stair stair_l from=deck_l to=balcony_l
piece table kind=table at=C size=(5,3)

scene 1.2 set=act1
HM @ DL
""",
        encoding="utf-8",
    )

    from stager.staging.block import main
    import sys

    original_argv = sys.argv
    try:
        sys.argv = [
            "block",
            "stage",
            str(source),
            "--out",
            str(svg_path),
            "--json-out",
            str(json_path),
        ]
        main()
        sys.argv = [
            "block",
            "set",
            str(source),
            "--set",
            "act1",
            "--out",
            str(set_svg_path),
            "--json-out",
            str(set_json_path),
        ]
        main()
    finally:
        sys.argv = original_argv

    svg = svg_path.read_text(encoding="utf-8")
    set_svg = set_svg_path.read_text(encoding="utf-8")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    set_data = json.loads(set_json_path.read_text(encoding="utf-8"))
    assert "Scene stage" in svg
    assert "<title>balcony +8</title>" not in svg
    assert "<title>table</title>" not in svg
    assert ">HM</text>" not in svg
    assert data["diagram_id"] == "stage"
    assert data["diagram_kind"] == "stage"
    assert data["entities"] == []
    assert data["levels"] == []
    assert "Scene set:act1" in set_svg
    assert "<title>balcony +8</title>" in set_svg
    assert "<title>table</title>" in set_svg
    assert ">HM</text>" not in set_svg
    assert set_data["set_id"] == "act1"
    assert any(level["id"] == "balcony" for level in set_data["levels"])


def test_block_cli_uses_default_inputs_and_outputs_under_play_build_folder(tmp_path: Path, monkeypatch) -> None:
    play_dir = tmp_path / "plays" / "hamlet"
    play_dir.mkdir(parents=True)
    source = tmp_path / "build" / "hamlet" / "staging" / "staging.txt"
    source.parent.mkdir(parents=True)
    source.write_text(
        """
stage type=proscenium
grid standard=9
setup act1
piece table kind=table at=C size=(5,3)

scene 1.2 set=act1
HM @ DL

b1 @ 1.2-2
HM -> C
""",
        encoding="utf-8",
    )

    from stager.staging.block import main
    import sys

    monkeypatch.chdir(play_dir)
    original_argv = sys.argv
    try:
        sys.argv = ["block", "stage"]
        main()
        sys.argv = ["block", "set", "act1"]
        main()
        sys.argv = ["block", "scene", "1.2"]
        main()
        sys.argv = ["block", "beat", "1.2", "b1"]
        main()
    finally:
        sys.argv = original_argv

    output_dir = tmp_path / "build" / "hamlet" / "staging"
    assert (output_dir / "stage.svg").exists()
    assert (output_dir / "set-act1.svg").exists()
    assert (output_dir / "scene-1.2.svg").exists()
    assert (output_dir / "scene-1.2-b1.svg").exists()


def test_block_cli_keeps_option_based_scene_and_beat_args(tmp_path: Path) -> None:
    source = tmp_path / "staging.txt"
    scene_svg_path = tmp_path / "scene.svg"
    beat_svg_path = tmp_path / "beat.svg"
    source.write_text(
        """
stage type=proscenium
grid standard=9

scene 1.2
HM @ DL

b1 @ 1.2-2
HM -> C
""",
        encoding="utf-8",
    )

    from stager.staging.block import main
    import sys

    original_argv = sys.argv
    try:
        sys.argv = ["block", "scene", str(source), "--scene", "1.2", "--out", str(scene_svg_path)]
        main()
        sys.argv = [
            "block",
            "beat",
            str(source),
            "--scene",
            "1.2",
            "--beat",
            "b1",
            "--out",
            str(beat_svg_path),
        ]
        main()
    finally:
        sys.argv = original_argv

    assert "Scene 1.2" in scene_svg_path.read_text(encoding="utf-8")
    assert "Scene 1.2@b1" in beat_svg_path.read_text(encoding="utf-8")


def test_block_cli_icons_uses_default_output(capsys) -> None:
    from stager.staging.block import REPO_ROOT, main
    import sys

    output_path = REPO_ROOT / "build" / "staging" / "block-icon-library.svg"
    original_argv = sys.argv
    try:
        sys.argv = ["block", "icons"]
        main()
    finally:
        sys.argv = original_argv

    assert '<symbol id="stage-icon-table"' in output_path.read_text(encoding="utf-8")
    assert capsys.readouterr().out.strip() == "build/staging/block-icon-library.svg"
