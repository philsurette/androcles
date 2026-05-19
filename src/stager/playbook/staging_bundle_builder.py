from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from stager.playbook.app_staging import AppStaging
from stager.shared import paths
from stager.staging.diagram_state_builder import DiagramStateBuilder
from stager.staging.model import BlockingBeat, StagingDocument
from stager.staging.parser import StagingParser
from stager.staging.resolver import StagingResolver
from stager.staging.state_resolver import StagingStateResolver
from stager.staging.svg_icons import StageSvgIconLibrary


BUNDLE_FORMAT = "quince.blocking.diagram_bundle"
BUNDLE_FORMAT_VERSION = "1.0.0"
DELTA_FORMAT = "quince.blocking.diagram_delta"
DELTA_FORMAT_VERSION = "1.0.0"


@dataclass(frozen=True)
class StagingBundleResult:
    manifest_entry: AppStaging
    manifest_path: Path
    file_paths: tuple[Path, ...]


class PlaybookStagingBundleBuilder:
    def __init__(self, *, paths_config: paths.PathConfig, app_dir: Path) -> None:
        self.paths_config = paths_config
        self.app_dir = app_dir
        self.bundle_dir = app_dir / "staging"
        self.diagram_builder = DiagramStateBuilder()

    def build(self) -> StagingBundleResult | None:
        staging_path = self.paths_config.build_dir / "staging" / "staging.txt"
        if not staging_path.exists():
            return None
        document = StagingParser().parse(staging_path.read_text(encoding="utf-8"))
        if not document.snapshots:
            return None
        self.bundle_dir.mkdir(parents=True, exist_ok=True)
        (self.bundle_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
        (self.bundle_dir / "deltas").mkdir(parents=True, exist_ok=True)

        checkpoint_records: list[dict[str, Any]] = []
        delta_records: list[dict[str, Any]] = []
        file_paths: list[Path] = []
        icons_path = self.bundle_dir / "icons.svg"
        icons_path.write_text("\n".join(StageSvgIconLibrary().defs()) + "\n", encoding="utf-8")
        file_paths.append(icons_path)
        for scene_id in sorted(document.snapshots):
            checkpoint_state = self._scene_state(document, scene_id)
            checkpoint_id = f"scene:{scene_id}:start"
            checkpoint_path = self.bundle_dir / "checkpoints" / f"{self._path_id(scene_id)}-start.json"
            self._write_json(checkpoint_path, checkpoint_state)
            file_paths.append(checkpoint_path)
            checkpoint_records.append(
                {
                    "id": checkpoint_id,
                    "scene_id": scene_id,
                    "beat_id": None,
                    "production_anchor": self._scene_anchor(document, scene_id),
                    "path": self._manifest_path(checkpoint_path),
                }
            )
            for beat in self._beats_for_scene(document, scene_id):
                target_state = self._beat_state(document, scene_id, beat.beat_id)
                delta_path = self.bundle_dir / "deltas" / f"{self._path_id(scene_id)}-{self._path_id(beat.beat_id)}.json"
                target_id = target_state["diagram_id"]
                delta = self._delta(
                    from_checkpoint=checkpoint_id,
                    target_id=target_id,
                    scene_id=scene_id,
                    beat=beat,
                    checkpoint_state=checkpoint_state,
                    target_state=target_state,
                )
                self._write_json(delta_path, delta)
                file_paths.append(delta_path)
                delta_records.append(
                    {
                        "id": target_id,
                        "scene_id": scene_id,
                        "beat_id": beat.beat_id,
                        "production_anchor": beat.script_anchor,
                        "from_checkpoint": checkpoint_id,
                        "path": self._manifest_path(delta_path),
                    }
                )

        manifest = {
            "format": BUNDLE_FORMAT,
            "format_version": BUNDLE_FORMAT_VERSION,
            "default_orientation": "portrait",
            "icon_library": {
                "format": "svg-symbols",
                "path": self._manifest_path(icons_path),
            },
            "checkpoints": checkpoint_records,
            "deltas": delta_records,
        }
        manifest_path = self.bundle_dir / "diagram_manifest.json"
        self._write_json(manifest_path, manifest)
        file_paths.append(manifest_path)
        return StagingBundleResult(
            manifest_entry=AppStaging(
                included=True,
                format=BUNDLE_FORMAT,
                format_version=BUNDLE_FORMAT_VERSION,
                manifest_path=self._manifest_path(manifest_path),
            ),
            manifest_path=manifest_path,
            file_paths=tuple(file_paths),
        )

    def _scene_state(self, document: StagingDocument, scene_id: str) -> dict[str, Any]:
        snapshot = StagingResolver().resolve_snapshot(document, scene_id)
        return self.diagram_builder.build(snapshot).to_dict()

    def _beat_state(self, document: StagingDocument, scene_id: str, beat_id: str) -> dict[str, Any]:
        snapshot = StagingStateResolver().resolve_beat(document, scene_id, beat_id)
        return self.diagram_builder.build(snapshot).to_dict()

    def _beats_for_scene(self, document: StagingDocument, scene_id: str) -> tuple[BlockingBeat, ...]:
        return tuple(beat for beat in document.beats if beat.scene_id == scene_id)

    def _scene_anchor(self, document: StagingDocument, scene_id: str) -> str | None:
        return None

    def _delta(
        self,
        *,
        from_checkpoint: str,
        target_id: str,
        scene_id: str,
        beat: BlockingBeat,
        checkpoint_state: dict[str, Any],
        target_state: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "format": DELTA_FORMAT,
            "format_version": DELTA_FORMAT_VERSION,
            "from_checkpoint": from_checkpoint,
            "targets": [
                {
                    "target_id": target_id,
                    "scene_id": scene_id,
                    "beat_id": beat.beat_id,
                    "production_anchor": beat.script_anchor,
                    "ops": self._ops(checkpoint_state, target_state),
                }
            ],
        }

    def _ops(self, checkpoint_state: dict[str, Any], target_state: dict[str, Any]) -> list[dict[str, Any]]:
        ops: list[dict[str, Any]] = []
        for collection, id_field, upsert_op, remove_op in (
            ("set_pieces", "id", "upsert_entity", "remove_entity"),
            ("entities", "id", "upsert_entity", "remove_entity"),
            ("offstage", "id", "upsert_offstage", "remove_offstage"),
        ):
            ops.extend(self._collection_ops(checkpoint_state, target_state, collection, id_field, upsert_op, remove_op))
        if checkpoint_state.get("diagnostics", []) != target_state.get("diagnostics", []):
            ops.append({"op": "replace_diagnostics", "diagnostics": target_state.get("diagnostics", [])})
        return ops

    def _collection_ops(
        self,
        checkpoint_state: dict[str, Any],
        target_state: dict[str, Any],
        collection: str,
        id_field: str,
        upsert_op: str,
        remove_op: str,
    ) -> list[dict[str, Any]]:
        before = {item[id_field]: item for item in checkpoint_state.get(collection, [])}
        after = {item[id_field]: item for item in target_state.get(collection, [])}
        ops: list[dict[str, Any]] = []
        for item_id in sorted(before.keys() - after.keys()):
            ops.append({"op": remove_op, "id": item_id})
        for item_id in sorted(after):
            if before.get(item_id) != after[item_id]:
                key = "entity" if upsert_op == "upsert_entity" else "offstage"
                ops.append({"op": upsert_op, key: deepcopy(after[item_id])})
        return ops

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    def _manifest_path(self, path: Path) -> str:
        return path.relative_to(self.app_dir).as_posix()

    def _path_id(self, value: str) -> str:
        return value.replace(":", "-").replace("/", "-")
