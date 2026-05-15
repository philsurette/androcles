from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json

from stager.production_publication.published_recording_request_builder import PublishedRecordingRequestBuilder
from stager.production_publication.published_version import PublishedVersion
from stager.production_publication.production_change_analyzer import ProductionChangeAnalyzer
from stager.production_publication.production_publish_result import ProductionPublishResult
from stager.production_publication.production_snapshot_builder import ProductionSnapshotBuilder
from stager.production_publication.production_source_rewriter import ProductionSourceRewriter
from stager.production_publication.production_version_store import ProductionVersionStore
from stager.scriptwright import ProductionPlayLoader, ProductionScriptParser, ScriptWright
from stager.shared import paths


@dataclass
class ProductionPublisher:
    paths_config: paths.PathConfig

    def publish(
        self,
        *,
        apply_id_updates: bool = False,
        allow_id_reuse: bool = False,
        recording_requests: bool = False,
    ) -> ProductionPublishResult:
        production = self._locked_source()
        store = ProductionVersionStore(self.paths_config)
        previous = store.current()
        snapshot_builder = ProductionSnapshotBuilder()
        analyzer = ProductionChangeAnalyzer()
        report = analyzer.analyze(
            previous=previous,
            current_lines=snapshot_builder.build_lines(production),
        )

        id_updates = {
            change.line_id: change.recommended_id
            for change in report.changed_id_reuse
            if change.recommended_id is not None
        }
        changed_reasons = self._changed_line_reasons(report, id_updates, apply_id_updates)

        if id_updates and apply_id_updates:
            rewriter = ProductionSourceRewriter(self.paths_config)
            production = rewriter.rewrite_ids(production, id_updates)
            rewriter.write_locked(production)
            report = analyzer.analyze(
                previous=previous,
                current_lines=snapshot_builder.build_lines(production),
            )
        elif id_updates and not allow_id_reuse:
            raise RuntimeError(self._id_reuse_message(id_updates))

        version = PublishedVersion(
            version=store.next_version_number(),
            published_at=self._now(),
            source_path=paths.display_path(self.paths_config.production_markdown),
            lines=snapshot_builder.build_lines(production),
        )
        store.save(
            version=version,
            source_path=self.paths_config.production_markdown,
            change_report=report,
        )

        request_paths = ()
        if recording_requests:
            line_reasons = self._line_reasons(report, changed_reasons)
            if line_reasons:
                build_id, build_timestamp = _read_playbook_build_metadata(self.paths_config)
                request_paths = tuple(
                    PublishedRecordingRequestBuilder(
                        play=ProductionPlayLoader(paths_config=self.paths_config).load(),
                        paths_config=self.paths_config,
                        line_reasons=line_reasons,
                        version_label=version.label,
                        build_id=build_id,
                        build_timestamp=build_timestamp,
                    ).build()
                )

        return ProductionPublishResult(
            version=version,
            change_report=report,
            id_updates=id_updates,
            recording_request_paths=request_paths,
        )

    def diff(self):
        production = self._locked_source(write_locked=False)
        store = ProductionVersionStore(self.paths_config)
        return ProductionChangeAnalyzer().analyze(
            previous=store.current(),
            current_lines=ProductionSnapshotBuilder().build_lines(production),
        )

    def _locked_source(self, write_locked: bool = True):
        if not self.paths_config.production_markdown.exists():
            raise RuntimeError(
                "Missing production script "
                f"{paths.display_path(self.paths_config.production_markdown)}; run './main scriptwright lock' first."
            )
        production = ProductionScriptParser(self.paths_config.production_markdown).parse_path()
        if production.locked:
            return production
        if not write_locked:
            return production
        ScriptWright(paths_config=self.paths_config).write_locked()
        return ProductionScriptParser(self.paths_config.production_markdown).parse_path()

    def _line_reasons(self, report, changed_reasons: dict[str, str]) -> dict[str, str]:
        reasons = dict(changed_reasons)
        for change in report.added:
            if change.current is not None and change.current.roles:
                reasons.setdefault(change.current.id, "script_added")
        if report.base_version is None:
            return {}
        return reasons

    def _changed_line_reasons(
        self,
        report,
        id_updates: dict[str, str],
        apply_id_updates: bool,
    ) -> dict[str, str]:
        reasons: dict[str, str] = {}
        for change in report.changed_id_reuse:
            if change.current is None or not change.current.roles:
                continue
            line_id = id_updates[change.line_id] if apply_id_updates and change.line_id in id_updates else change.line_id
            reasons[line_id] = "script_changed"
        return reasons

    def _id_reuse_message(self, id_updates: dict[str, str]) -> str:
        lines = ["Changed production ids were reused. Apply recommended revisions first:"]
        for old_id, new_id in sorted(id_updates.items()):
            lines.append(f"  {old_id} -> {new_id}")
        return "\n".join(lines)

    def _now(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_playbook_build_metadata(paths_config: paths.PathConfig) -> tuple[str | None, str | None]:
    manifest_path = paths_config.build_dir / "app" / "manifest.json"
    if not manifest_path.exists():
        return None, None
    try:
        raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None, None
    build = raw_manifest.get("build") if isinstance(raw_manifest, dict) else None
    if not isinstance(build, dict):
        return None, None
    build_id = build.get("buildId")
    build_timestamp = build.get("buildTimestamp")
    return (
        build_id if isinstance(build_id, str) and build_id else None,
        build_timestamp if isinstance(build_timestamp, str) and build_timestamp else None,
    )
