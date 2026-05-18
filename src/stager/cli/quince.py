from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import click
import typer
from ruamel.yaml import YAML

from stager.production.cast_config_service import CastConfigService
from stager.production.audio_output_workflow_service import AudioOutputWorkflowService
from stager.production.production_recommendation import ProductionRecommendationService
from stager.production.production_renderers import (
    render_cast_config,
    render_production_change_report,
    render_production_recommendation,
    render_production_status,
    render_quince_context,
)
from stager.production.production_status import ProductionStatusService
from stager.production.quince_context import QuinceContext, QuinceContextResolver, QuinceWorkspaceConfig
from stager.production.recording_workflow_service import RecordingWorkflowService
from stager.production_publication.production_source_resolver import ProductionSourceResolver
from stager.production_publication.production_publisher import ProductionPublisher
from stager.scriptwright import ProductionPlayLoader


app = typer.Typer(
    add_completion=False,
    pretty_exceptions_enable=False,
    help="Producer workflow CLI for Quince productions.",
)
cast_app = typer.Typer(
    add_completion=False,
    pretty_exceptions_enable=False,
    help="Show and edit cast assignments.",
)
app.add_typer(cast_app, name="cast")

PlayOption = Annotated[str | None, typer.Option("--play", "-p", help="Production id under plays/.")]
WorkspaceOption = Annotated[
    Path | None,
    typer.Option("--workspace", help="Quince workspace root. Defaults to current-directory discovery."),
]
ProductionSourceOption = Annotated[
    str,
    typer.Option(
        "--production-source",
        "-ps",
        help="Production source: working, published, or auto. Producer status defaults to working.",
    ),
]
FormatOption = Annotated[str, typer.Option("--format", help="Output format: text, yaml, or json.")]


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Start with `quince status` or `quince next`."""
    if ctx.invoked_subcommand is None:
        typer.echo("Start with `quince status` or `quince next`. Use `quince --help` to see commands.")
        raise typer.Exit(code=0)


@app.command("list")
def list_productions(workspace: WorkspaceOption = None) -> None:
    """List productions in the current Quince workspace."""
    try:
        resolver = QuinceContextResolver(workspace=workspace)
        workspace_root = resolver.resolve_workspace_root()
        play_ids = resolver.play_ids(workspace_root)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    if not play_ids:
        typer.echo("No productions found.")
        return
    typer.echo(f"Productions in {workspace_root.as_posix()}:")
    for play_id in play_ids:
        typer.echo(f"  {play_id}")


@app.command("use")
def use_production(play_id: str, workspace: WorkspaceOption = None) -> None:
    """Set the workspace-local active production."""
    try:
        resolver = QuinceContextResolver(workspace=workspace)
        workspace_root = resolver.resolve_workspace_root()
        resolver.resolve_play_id(workspace_root, play_id=play_id)
        config_path = resolver.save_workspace_config(
            workspace_root,
            QuinceWorkspaceConfig(active_play=play_id),
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(f"Active production: {play_id}")
    typer.echo(f"Wrote {config_path.relative_to(workspace_root).as_posix()}")


@app.command("status")
def status(
    play: PlayOption = None,
    workspace: WorkspaceOption = None,
    output_format: FormatOption = "text",
    production_source: ProductionSourceOption = "working",
) -> None:
    """Show production, cast, recording, and Playbook readiness."""
    if output_format not in ("text", "yaml", "json"):
        raise typer.BadParameter("format must be text, yaml, or json")
    try:
        context = _resolve_context(play=play, workspace=workspace, production_source=production_source)
        status_model = _production_status(context)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    payload = {
        "context": context.to_dict(),
        "status": status_model.to_dict(),
    }
    if output_format == "json":
        typer.echo(json.dumps(payload, indent=2) + "\n")
    elif output_format == "yaml":
        yaml = YAML()
        yaml.default_flow_style = False
        from io import StringIO

        output = StringIO()
        yaml.dump(payload, output)
        typer.echo(output.getvalue())
    else:
        typer.echo(render_quince_context(context))
        typer.echo(render_production_status(status_model))


@app.command("changes")
def changes(play: PlayOption = None, workspace: WorkspaceOption = None) -> None:
    """Show changes between working production.md and the current published version."""
    try:
        context = _resolve_context(play=play, workspace=workspace, production_source="working")
        result = ProductionPublisher(paths_config=context.path_config).diff_with_versions()
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    current_label = result.current_version.label if result.current_version is not None else "none"
    working_label = str(result.working_production_version) if result.working_production_version is not None else "unpublished"
    typer.echo(render_quince_context(context))
    typer.echo(f"Current published production: {current_label}")
    typer.echo(f"Working production version: {working_label}")
    typer.echo(f"Working source has unpublished changes: {'yes' if result.change_report.changes else 'no'}")
    if result.current_version is not None and result.working_production_version is None:
        typer.echo("Lineage warning: working production has no production_version metadata.")
    elif (
        result.current_version is not None
        and result.working_production_version is not None
        and result.working_production_version != result.current_version.production_version
    ):
        typer.echo(
            "Lineage warning: working production is based on "
            f"{result.working_production_version}, not current {result.current_version.production_version}."
        )
    typer.echo(
        render_production_change_report(
            result.change_report,
            base_label=current_label if result.current_version is not None else None,
        )
    )


@app.command("publish")
def publish(
    play: PlayOption = None,
    workspace: WorkspaceOption = None,
    change_summary: str | None = typer.Option(
        None,
        "--change-summary",
        help="Producer-authored summary of the manuscript changes being published.",
    ),
    allow_empty_summary: bool = typer.Option(
        False,
        "--allow-empty-summary",
        help="Publish without a change summary.",
    ),
    recording_requests: bool = typer.Option(
        False,
        "--recording-requests",
        help="Generate Recording Requests for changed and added role lines.",
    ),
    apply_id_updates: bool = typer.Option(
        False,
        "--apply-id-updates",
        help="Rewrite changed spoken lines to fresh recommended ids before publishing.",
    ),
    allow_id_reuse: bool = typer.Option(
        False,
        "--allow-id-reuse",
        help="Keep changed spoken text under the same production ids; use only when downstream recordings should be treated as reusable.",
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show changes without publishing."),
) -> None:
    """Publish working production.md as a new production version."""
    try:
        context = _resolve_context(play=play, workspace=workspace, production_source="working")
        publisher = ProductionPublisher(paths_config=context.path_config)
        diff = publisher.diff_with_versions()
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    current_label = diff.current_version.label if diff.current_version is not None else "none"
    typer.echo(render_quince_context(context))
    typer.echo(render_production_change_report(diff.change_report, base_label=current_label if diff.current_version else None))
    if dry_run:
        typer.echo("Dry run: no production version was published.")
        return
    summary = (change_summary or "").strip()
    if not summary and not allow_empty_summary:
        summary = typer.prompt("Change summary", default="", show_default=False).strip()
    if not summary and not allow_empty_summary:
        raise click.ClickException("Publishing requires --change-summary or --allow-empty-summary.")
    try:
        result = publisher.publish(
            apply_id_updates=apply_id_updates,
            allow_id_reuse=allow_id_reuse,
            recording_requests=recording_requests,
            change_summary=summary,
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(f"Published production {result.version.label}.")
    if result.id_updates:
        typer.echo(
            "Rewrote changed spoken lines to fresh production ids:"
            if apply_id_updates
            else "Changed spoken lines need fresh production ids before publishing:"
        )
        for old_id, new_id in sorted(result.id_updates.items()):
            typer.echo(f"  {old_id} -> {new_id}")
    if result.recording_request_paths:
        typer.echo("Generated Recording Requests:")
        for request_path in result.recording_request_paths:
            typer.echo(f"  {request_path.relative_to(context.workspace_root).as_posix()}")


@app.command("send-requests")
def send_requests(
    play: PlayOption = None,
    workspace: WorkspaceOption = None,
    role: str | None = typer.Option(None, "--role", "-r", help="Limit requests to one role."),
    actor: str | None = typer.Option(None, "--actor", help="Limit requests to roles assigned to this actor id."),
    changed_only: bool = typer.Option(False, "--changed-only", help="Request only changed or added production lines."),
    missing_only: bool = typer.Option(False, "--missing-only", help="Request only segments that are missing audio."),
    notes: str | None = typer.Option(None, "--notes", help="Optional notes included in each Recording Request."),
) -> None:
    """Build LineRecorder Recording Request packages."""
    try:
        context, service = _recording_service(play=play, workspace=workspace)
        result = service.send_requests(
            role=role,
            actor=actor,
            changed_only=changed_only,
            missing_only=missing_only,
            notes=notes,
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(render_quince_context(context))
    if result.requests:
        typer.echo("Generated Recording Requests:")
        for request in result.requests:
            actor_text = f", actor {request.actor}" if request.actor is not None else ""
            typer.echo(
                "  "
                f"{request.role}: {request.item_count} items, {request.request_kind}{actor_text} -> "
                f"{request.path.relative_to(context.workspace_root).as_posix()}"
            )
    else:
        typer.echo("No Recording Requests generated.")
    if result.skipped_whole_role_roles:
        typer.echo("Skipped whole-role roles: " + ", ".join(result.skipped_whole_role_roles))


@app.command("receive-recordings")
def receive_recordings(
    package: Path = typer.Argument(..., help="LineRecorder role recordings zip to import."),
    play: PlayOption = None,
    workspace: WorkspaceOption = None,
    denoise: bool = typer.Option(False, "--denoise", help="Use included floor-noise recordings for import-time denoising."),
    trim_silence: bool = typer.Option(False, "--trim-silence", help="Trim leading and trailing silence during import."),
) -> None:
    """Import a LineRecorder role recordings package."""
    try:
        context, service = _recording_service(play=play, workspace=workspace)
        result = service.receive_recordings(package_path=package, denoise=denoise, trim_silence=trim_silence)
        status_model = ProductionStatusService(paths_config=context.path_config, play=service.play).build()
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    status = "complete" if result.complete else "partial"
    typer.echo(render_quince_context(context))
    typer.echo(f"Imported {result.imported_count} {status} recordings for {result.role}.")
    if result.missing_segment_ids:
        typer.echo("Missing segments: " + ", ".join(result.missing_segment_ids))
    for issue in result.issues:
        typer.echo(f"Warning [{issue.code}]: {issue.message}")
    typer.echo(f"Import transaction: {result.transaction_manifest_path.relative_to(context.workspace_root).as_posix()}")
    role_status = next((candidate for candidate in status_model.roles if candidate.role == result.role), None)
    if role_status is not None:
        typer.echo(
            f"{role_status.role}: {role_status.recorded_segments}/{role_status.expected_segments} segments, "
            f"{len(role_status.missing_segments)} missing"
        )


@app.command("split-recordings")
def split_recordings(
    play: PlayOption = None,
    workspace: WorkspaceOption = None,
    role: str | None = typer.Option(None, "--role", "-r", help="Limit splitting to one role."),
    include_linerecorder: bool = typer.Option(
        False,
        "--include-linerecorder",
        help="Allow splitting roles configured for LineRecorder instead of only whole-role roles.",
    ),
    silence_thresh: int = typer.Option(-60, "--silence-thresh", help="Silence threshold in dBFS."),
    separator_len_ms: int = typer.Option(1700, "--separator-len-ms", help="Minimum separator silence length in ms."),
    chunk_size: int = typer.Option(50, "--chunk-size", help="Number of snippets per split chunk."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing exported recordings and segments."),
) -> None:
    """Split whole-role source recordings into segment audio."""
    try:
        context, service = _recording_service(play=play, workspace=workspace)
        result = service.split_recordings(
            role=role,
            include_linerecorder=include_linerecorder,
            silence_thresh=silence_thresh,
            separator_len_ms=separator_len_ms,
            chunk_size=chunk_size,
            force=force,
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(render_quince_context(context))
    if result.roles:
        typer.echo("Split recordings for: " + ", ".join(result.roles))
    else:
        typer.echo("No whole-role recordings selected for splitting.")
    if result.skipped_linerecorder_roles:
        typer.echo("Skipped LineRecorder roles: " + ", ".join(result.skipped_linerecorder_roles))


@app.command("prepare-audio")
def prepare_audio(
    play: PlayOption = None,
    workspace: WorkspaceOption = None,
    role: str | None = typer.Option(None, "--role", "-r", help="Limit preparation to one role."),
    profile: str | None = typer.Option(None, "--profile", help="Override the resolved cleanup profile."),
    use_analysis: bool = typer.Option(False, "--use-analysis", help="Use cleanup analysis recommendations."),
    run: bool = typer.Option(False, "--run", help="Run safe preparation/rendering steps."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Plan without rendering audio."),
    force: bool = typer.Option(False, "--force", help="Re-render even when caches are current."),
    audio_source: str = typer.Option("auto", "--audio-source", help="Voice source audio: auto, canonical, or cleaned."),
    voice_actor: str | None = typer.Option(None, "--voice-actor", help="Select actor for voice-profile rendering."),
) -> None:
    """Plan or render non-destructive audio preparation."""
    try:
        context, service = _audio_output_service(play=play, workspace=workspace, production_source="working")
        result = service.prepare_audio(
            role=role,
            profile=profile,
            use_analysis=use_analysis,
            run=run and not dry_run,
            force=force,
            audio_source=audio_source,
            voice_actor=voice_actor,
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(render_quince_context(context))
    mode = "Dry run" if result.dry_run else "Prepared"
    typer.echo(f"{mode} audio preparation.")
    typer.echo(f"Missing canonical segment recordings: {result.status.missing_recording_count}")
    typer.echo(f"Cleanup profiles: {len(result.cleanup_plan.entries)} planned entries")
    typer.echo(f"Voice profiles: {result.voice_profile_count} configured")
    if result.cleanup_analysis is not None:
        typer.echo(f"Cleanup analysis: {result.cleanup_analysis.entry_count} segments")
        typer.echo(_relative(context, result.cleanup_analysis.markdown_path))
    if result.prepared_batches:
        typer.echo(f"Prepared cleanup batches: {len(result.prepared_batches)}")
    if result.rendered_batches:
        rendered_segments = sum(batch.rendered_count for batch in result.rendered_batches)
        typer.echo(f"Rendered cleaned segments: {rendered_segments}")
    if result.voice_results:
        rendered_voice = sum(1 for item in result.voice_results if item.rendered)
        typer.echo(f"Rendered voice-profile segments: {rendered_voice}")


@app.command("build-playbook")
def build_playbook(
    play: PlayOption = None,
    workspace: WorkspaceOption = None,
    production_source: ProductionSourceOption = "auto",
    allow_working_source: bool = typer.Option(
        False,
        "--allow-working-source",
        help="Allow building from an unpublished working production.md.",
    ),
    audio_format: str = typer.Option("wav", "--audio-format", help="Playbook audio format: wav or mp3."),
    audio_source: str = typer.Option("auto", "--audio-source", help="Segment audio source: auto, canonical, or cleaned."),
    voice_profiles: bool = typer.Option(False, "--voice-profiles/--no-voice-profiles", help="Use rendered voice-profile audio."),
    voice_actor: str | None = typer.Option(None, "--voice-actor", help="Select actor for voice-profile rendering."),
    build_type: str | None = typer.Option(None, "--build-type", help="Override configured build type."),
) -> None:
    """Build a Cuemaster Playbook package."""
    try:
        context, service, source_kind = _audio_output_service_for_build(
            play=play,
            workspace=workspace,
            production_source=production_source,
            allow_working_source=allow_working_source,
        )
        result = service.build_playbook(
            build_type=build_type,
            audio_format=audio_format,
            audio_source=audio_source,
            voice_profiles=voice_profiles,
            voice_actor=voice_actor,
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(render_quince_context(context))
    typer.echo(f"Built Playbook from {source_kind} source.")
    typer.echo(f"Audio source: {result.audio_source}")
    for output_path in result.paths:
        typer.echo(_relative(context, output_path))


@app.command("build-audioplay")
def build_audioplay(
    play: PlayOption = None,
    workspace: WorkspaceOption = None,
    production_source: ProductionSourceOption = "auto",
    allow_working_source: bool = typer.Option(
        False,
        "--allow-working-source",
        help="Allow building from an unpublished working production.md.",
    ),
    part: str | None = typer.Option(None, "--part", help="Part number to assemble."),
    audio_format: str = typer.Option("mp4", "--audio-format", help="Output format: mp4, mp3, or wav."),
    audio_source: str = typer.Option("auto", "--audio-source", help="Segment audio source: auto, canonical, or cleaned."),
    voice_profiles: bool = typer.Option(False, "--voice-profiles/--no-voice-profiles", help="Use rendered voice-profile audio."),
    voice_actor: str | None = typer.Option(None, "--voice-actor", help="Select actor for voice-profile rendering."),
    normalize_output: bool = typer.Option(True, "--normalize/--no-normalize", help="Normalize generated audioplay output."),
    prepare: bool = typer.Option(True, "--prepare/--no-prepare", help="Prepare text artifacts and segments before building."),
) -> None:
    """Build assembled audioplay output."""
    try:
        context, service, source_kind = _audio_output_service_for_build(
            play=play,
            workspace=workspace,
            production_source=production_source,
            allow_working_source=allow_working_source,
        )
        result = service.build_audioplay(
            part=part,
            audio_format=audio_format,
            audio_source=audio_source,
            voice_profiles=voice_profiles,
            voice_actor=voice_actor,
            normalize_output=normalize_output,
            prepare=prepare,
        )
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(render_quince_context(context))
    typer.echo(f"Built audioplay from {source_kind} source.")
    typer.echo(f"Audio source: {result.audio_source}")
    for output_path in result.paths:
        typer.echo(_relative(context, output_path))


@cast_app.command("show")
def cast_show(play: PlayOption = None, workspace: WorkspaceOption = None) -> None:
    """Show cast assignments for the selected production."""
    try:
        context, service = _cast_service(play=play, workspace=workspace)
        config = service.load()
        validation = service.validate(config)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(render_quince_context(context))
    typer.echo(render_cast_config(config, validation))


@cast_app.command("check")
def cast_check(play: PlayOption = None, workspace: WorkspaceOption = None) -> None:
    """Validate cast assignments for the selected production."""
    try:
        context, service = _cast_service(play=play, workspace=workspace)
        config = service.load()
        validation = service.validate(config)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(render_quince_context(context))
    typer.echo(render_cast_config(config, validation))
    if not validation.ok:
        raise typer.Exit(code=1)


@cast_app.command("assign")
def cast_assign(
    role: str,
    actor: str,
    play: PlayOption = None,
    workspace: WorkspaceOption = None,
    recording: str | None = typer.Option(None, "--recording", help="Recording method: linerecorder or whole-role."),
) -> None:
    """Assign an actor id to a role in cast.yaml."""
    try:
        context, service = _cast_service(play=play, workspace=workspace)
        config = service.assign(role=role, actor=actor, recording=recording)
        validation = service.validate(config)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    typer.echo(f"Assigned {actor} to {role}.")
    typer.echo(f"Wrote {(context.path_config.play_dir / 'cast.yaml').relative_to(context.workspace_root).as_posix()}")
    if validation.unassigned_roles:
        typer.echo("Unassigned roles: " + ", ".join(validation.unassigned_roles))


@app.command("next")
def next_step(
    play: PlayOption = None,
    workspace: WorkspaceOption = None,
    production_source: ProductionSourceOption = "working",
) -> None:
    """Show the next recommended producer action."""
    try:
        context = _resolve_context(play=play, workspace=workspace, production_source=production_source)
        status_model = _production_status(context)
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc

    recommendation = ProductionRecommendationService().recommend(status=status_model, play_id=context.play_id)
    typer.echo(render_production_recommendation(recommendation=recommendation, context=context))


def _resolve_context(*, play: str | None, workspace: Path | None, production_source: str) -> QuinceContext:
    if production_source not in ("working", "published", "auto"):
        raise RuntimeError("production source must be working, published, or auto")
    return QuinceContextResolver(workspace=workspace).resolve(
        play_id=play,
        production_source=production_source,
    )


def _production_status(context: QuinceContext):
    cfg = context.path_config
    if context.production_source != "working":
        ProductionSourceResolver(cfg).apply_to(context.production_source)
    play = ProductionPlayLoader(paths_config=cfg).load()
    return ProductionStatusService(paths_config=cfg, play=play).build()


def _cast_service(*, play: str | None, workspace: Path | None) -> tuple[QuinceContext, CastConfigService]:
    context = _resolve_context(play=play, workspace=workspace, production_source="working")
    loaded_play = ProductionPlayLoader(paths_config=context.path_config).load()
    return context, CastConfigService(paths_config=context.path_config, play=loaded_play)


def _recording_service(*, play: str | None, workspace: Path | None) -> tuple[QuinceContext, RecordingWorkflowService]:
    context = _resolve_context(play=play, workspace=workspace, production_source="working")
    loaded_play = ProductionPlayLoader(paths_config=context.path_config).load()
    return context, RecordingWorkflowService(paths_config=context.path_config, play=loaded_play)


def _audio_output_service(
    *,
    play: str | None,
    workspace: Path | None,
    production_source: str,
) -> tuple[QuinceContext, AudioOutputWorkflowService]:
    context = _resolve_context(play=play, workspace=workspace, production_source=production_source)
    loaded_play = ProductionPlayLoader(paths_config=context.path_config).load()
    return context, AudioOutputWorkflowService(paths_config=context.path_config, play=loaded_play)


def _audio_output_service_for_build(
    *,
    play: str | None,
    workspace: Path | None,
    production_source: str,
    allow_working_source: bool,
) -> tuple[QuinceContext, AudioOutputWorkflowService, str]:
    context = _resolve_context(play=play, workspace=workspace, production_source=production_source)
    resolver = ProductionSourceResolver(context.path_config)
    resolved_source = resolver.resolve(production_source)
    if resolved_source.kind == "working" and not allow_working_source:
        raise RuntimeError("Building from working production.md requires --allow-working-source.")
    context.path_config.production_markdown = resolved_source.path
    loaded_play = ProductionPlayLoader(paths_config=context.path_config).load()
    return (
        context,
        AudioOutputWorkflowService(paths_config=context.path_config, play=loaded_play),
        resolved_source.kind,
    )


def _relative(context: QuinceContext, path: Path) -> str:
    try:
        return path.relative_to(context.workspace_root).as_posix()
    except ValueError:
        return path.as_posix()


def main_cli() -> None:
    app()


if __name__ == "__main__":
    main_cli()
