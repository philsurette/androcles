from __future__ import annotations

from io import StringIO

from ruamel.yaml import YAML

from stager.production.production_recommendation import ProductionRecommendation
from stager.production.production_status import ProductionStatus
from stager.production.cast_config import CastConfig
from stager.production.cast_config_service import CastValidationResult
from stager.production.quince_context import QuinceContext


def render_quince_context(context: QuinceContext) -> str:
    return "\n".join(
        [
            f"Workspace: {context.workspace_root.as_posix()}",
            f"Production: {context.play_id} ({context.selection_source})",
            f"Source mode: {context.production_source}",
            "",
        ]
    )


def render_production_recommendation(
    *,
    recommendation: ProductionRecommendation,
    context: QuinceContext,
) -> str:
    return "\n".join(
        [
            f"Production: {context.play_id} ({context.selection_source})",
            f"Next: {recommendation.action}",
            f"Reason: {recommendation.reason}.",
            f"Command: {recommendation.command}",
        ]
    )


def render_cast_config(config: CastConfig, validation: CastValidationResult) -> str:
    lines: list[str] = ["Cast:"]
    if not config.actors:
        lines.append("  actors: none")
    else:
        lines.append("  actors:")
        for actor_id, actor in sorted(config.actors.items()):
            suffix = f" <{actor.email}>" if actor.email else ""
            lines.append(f"    {actor_id}: {actor.display_name}{suffix}")
    if not config.roles:
        lines.append("  roles: none")
    else:
        lines.append("  roles:")
        for role_id, assignment in sorted(config.roles.items()):
            actor = assignment.actor or "unassigned"
            voice = f", voice {assignment.voice_profile}" if assignment.voice_profile else ""
            lines.append(f"    {role_id}: {actor}, {assignment.recording}{voice}")
    if validation.unknown_roles:
        lines.extend(["", "Unknown roles: " + ", ".join(validation.unknown_roles)])
    if validation.unassigned_roles:
        lines.extend(["", "Unassigned roles: " + ", ".join(validation.unassigned_roles)])
    return "\n".join(lines)


def render_production_change_report(report, base_label: str | None = None) -> str:
    if report.base_version is None:
        return "No prior published production version."
    base = base_label or f"production sequence {report.base_version}"
    if not report.changes:
        return f"No production changes since {base}."
    lines = [f"Production changes since {base}:"]
    groups = [
        ("Needs recording", [change for change in report.changes if _needs_recording(change)]),
        ("Blocking only", list(report.blocking_changed)),
        ("Context only", list(report.context_changed)),
        ("Added", [change for change in report.added if not _needs_recording(change)]),
        ("Removed", list(report.removed)),
        ("Id issues", list(report.changed_id_reuse)),
    ]
    for heading, changes in groups:
        if not changes:
            continue
        lines.append(f"  {heading}:")
        for change in changes:
            lines.extend(f"    {line}" for line in _render_change_lines(change))
    return "\n".join(lines)


def _needs_recording(change) -> bool:
    return (
        change.current is not None
        and bool(change.current.roles)
        and change.kind in ("added", "changed_id_reuse")
    )


def _render_change_lines(change) -> list[str]:
    if change.kind == "changed_id_reuse":
        lines = [f"changed speech under reused id: {change.line_id} -> {change.recommended_id}"]
        if change.previous is not None:
            lines.append(f"old: {change.previous.text}")
        if change.current is not None:
            lines.append(f"new: {change.current.text}")
        return lines
    if change.kind == "added" and change.current is not None:
        return [f"added: {change.line_id} {change.current.text}"]
    if change.kind == "removed" and change.previous is not None:
        return [f"removed: {change.line_id} {change.previous.text}"]
    if change.kind == "context_changed" and change.current is not None:
        return [f"context changed: {change.line_id} {change.current.text}"]
    if change.kind == "blocking_changed" and change.current is not None:
        return [f"blocking changed: {change.line_id} {change.current.text}"]
    if change.kind == "blocking_added" and change.current is not None:
        return [f"blocking added: {change.line_id} {change.current.text}"]
    if change.kind == "blocking_removed" and change.previous is not None:
        return [f"blocking removed: {change.line_id} {change.previous.text}"]
    return [f"{change.kind}: {change.line_id}"]


def render_production_status(status: ProductionStatus) -> str:
    lines = [
        f"Production status for {status.play_id}: {status.play_title}",
        f"Current published version: {status.current_published_version or 'none'}",
        f"Working production version: {status.working_production_version or 'unpublished'}",
        f"Unpublished manuscript changes: {'yes' if status.has_unpublished_changes else 'no'}",
        f"Cast config: {'found' if status.cast_configured else 'missing'}",
        "",
        "Roles:",
    ]
    for role in status.roles:
        actor = role.actor or "unassigned"
        voice_profile = f", voice {role.voice_profile}" if role.voice_profile else ""
        missing = f", {len(role.missing_segments)} missing" if role.missing_segments else ""
        lines.append(
            f"  {role.role}: {actor}, {role.recording}, "
            f"{role.recorded_segments}/{role.expected_segments} segments{missing}{voice_profile}"
        )
    if status.unassigned_roles:
        lines.extend(["", "Unassigned roles: " + ", ".join(status.unassigned_roles)])
    if status.missing_recording_count:
        lines.extend(["", f"Missing segment recordings: {status.missing_recording_count}"])
    if status.stale_recording_count:
        stale = [
            f"{role.role}: {', '.join(role.stale_segments)}"
            for role in status.roles
            if role.stale_segments
        ]
        lines.extend(["", f"Stale imported recordings: {status.stale_recording_count}"])
        lines.extend(f"  {item}" for item in stale)
    if status.missing_source_recording_roles:
        lines.extend(
            [
                "",
                "Missing whole-role source recordings: " + ", ".join(status.missing_source_recording_roles),
            ]
        )
    if status.blocking_changes:
        lines.extend(["", f"Blocking changes needing Playbook rebuild: {len(status.blocking_changes)}"])
        lines.append("  " + ", ".join(status.blocking_changes))
    lines.extend(
        [
            "",
            "Cleanup review:",
            f"  exists: {'yes' if status.cleanup_review.exists else 'no'}",
            f"  reviewed: {status.cleanup_review.reviewed_segments}/{status.cleanup_review.expected_segments}",
        ]
    )
    if status.cleanup_review.exists:
        lines.append(f"  complete: {'yes' if status.cleanup_review.complete else 'no'}")
        if status.cleanup_review.missing_segments:
            lines.append(f"  missing review entries: {len(status.cleanup_review.missing_segments)}")
        if status.cleanup_review.missing_output_segments:
            lines.append(f"  missing output files: {len(status.cleanup_review.missing_output_segments)}")
        if status.cleanup_review.warning_count or status.cleanup_review.fallback_count:
            lines.append(
                f"  warnings: {status.cleanup_review.warning_count}, fallbacks: {status.cleanup_review.fallback_count}"
            )
    lines.extend(
        [
            "",
            "Voice profiles:",
            f"  configured profiles: {status.voice_profiles.configured_profiles}",
            f"  rendered: {status.voice_profiles.rendered_segments}/{status.voice_profiles.expected_segments}",
        ]
    )
    if status.voice_profiles.configured_profiles:
        lines.append(f"  complete: {'yes' if status.voice_profiles.complete else 'no'}")
        if status.voice_profiles.missing_segments:
            lines.append(f"  missing rendered segments: {len(status.voice_profiles.missing_segments)}")
    lines.extend(
        [
            "",
            "Playbook:",
            f"  exists: {'yes' if status.playbook.exists else 'no'}",
        ]
    )
    if status.playbook.exists:
        lines.append(f"  production version: {status.playbook.production_version or 'unknown'}")
        lines.append(f"  build id: {status.playbook.build_id or 'unknown'}")
        if status.playbook.matches_current_published_version is not None:
            lines.append(
                "  matches current published version: "
                + ("yes" if status.playbook.matches_current_published_version else "no")
            )
    return "\n".join(lines)


def render_production_status_yaml(status: ProductionStatus) -> str:
    yaml = YAML()
    output = StringIO()
    yaml.dump(status.to_dict(), output)
    return output.getvalue().rstrip()
