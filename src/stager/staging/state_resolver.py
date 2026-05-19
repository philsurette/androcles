from __future__ import annotations

from dataclasses import dataclass, replace

from stager.staging.diagnostics import StagingDiagnostic
from stager.staging.model import Placement, SceneSnapshot, StagingDocument
from stager.staging.resolver import StagingResolver


@dataclass
class StagingStateResolver:
    def resolve_beat(self, document: StagingDocument, scene_id: str, beat_id: str):
        diagnostics = list(document.diagnostics)
        snapshot = document.snapshots.get(scene_id)
        state: dict[str, Placement] = {}
        if snapshot is None:
            diagnostics.append(StagingDiagnostic("warning", f"Unknown scene snapshot {scene_id!r}"))
        else:
            for placement in snapshot.placements:
                state[placement.entity] = placement

        found_target = False
        for beat in document.beats:
            if beat.scene_id != scene_id:
                continue
            for placement in beat.placements:
                state[placement.entity] = placement
            if beat.beat_id == beat_id:
                found_target = True
                break

        if not found_target:
            diagnostics.append(StagingDiagnostic("warning", f"Unknown beat {beat_id!r} for scene {scene_id!r}"))

        effective_document = replace(
            document,
            snapshots={
                **document.snapshots,
                scene_id: SceneSnapshot(
                    scene_id=scene_id,
                    placements=tuple(state.values()),
                    line_no=snapshot.line_no if snapshot is not None else None,
                ),
            },
            diagnostics=tuple(diagnostics),
        )
        resolved = StagingResolver().resolve_snapshot(effective_document, scene_id)
        return replace(resolved, scene_id=f"{scene_id}@{beat_id}")
