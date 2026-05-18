from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import click
import typer
from ruamel.yaml import YAML

from stager.production.cast_config_service import CastConfigService
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
        help="Apply recommended revision ids before publishing changed reused ids.",
    ),
    allow_id_reuse: bool = typer.Option(
        False,
        "--allow-id-reuse",
        help="Publish changed text under reused production ids.",
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
        typer.echo("Applied id updates:" if apply_id_updates else "Recommended id updates:")
        for old_id, new_id in sorted(result.id_updates.items()):
            typer.echo(f"  {old_id} -> {new_id}")
    if result.recording_request_paths:
        typer.echo("Generated Recording Requests:")
        for request_path in result.recording_request_paths:
            typer.echo(f"  {request_path.relative_to(context.workspace_root).as_posix()}")


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


def main_cli() -> None:
    app()


if __name__ == "__main__":
    main_cli()
