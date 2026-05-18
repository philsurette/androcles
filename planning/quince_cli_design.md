# Quince Producer CLI Design

This document describes a producer-first Quince CLI that sits above the current Stager expert CLI. It is a product design, not a file-format contract. Stager implementation work belongs in [stager/quince_cli_implementation_plan.md](stager/quince_cli_implementation_plan.md).

## Problem

The current `./main` CLI is powerful, but it is organized as an expert build toolbox. It exposes implementation concepts such as `segments`, `scriptwright`, `production-source`, `whisper`, `normalize`, `cues`, `voice-render`, and `audio-cleanup render` at the top level.

That is useful for maintainers and automation, but it is not the right first surface for a producer whose questions are:

- Which production am I working on?
- Is the script current?
- What changed since the last version?
- Who needs to record what?
- Did I receive all recordings?
- Is the Playbook ready to send?
- What should I do next?

The producer-first CLI should answer those questions directly while reusing the same Stager services and artifacts.

## Goals

- Make common production workflows discoverable without knowing Stager internals.
- Support multiple productions cleanly.
- Infer the active production from the current directory when safe.
- Keep `production.md` as the editable source of truth.
- Keep the current Stager CLI available as the expert/legacy interface.
- Provide machine-readable output for future GUI, VS Code, or web UI surfaces.

## Non-Goals

- Do not replace LineRecorder or Cuemaster.
- Do not create a hosted backend or account model.
- Do not duplicate file contracts already defined under `planning/specs/`.
- Do not hide destructive actions behind broad "do everything" commands.

## Command Identity

Add a new console command:

```sh
quince
```

The existing `./main` and Stager Typer app remain available as the expert CLI. Documentation should lead with `quince` for producer workflows and point to `./main` for expert troubleshooting and lower-level build commands.

## Design Principles

- **Producer language first:** prefer `publish`, `send-requests`, `receive-recordings`, and `build-playbook` over implementation nouns.
- **Status before action:** commands that mutate or package artifacts should explain the relevant current state first or provide `--dry-run`.
- **Safe defaults:** default to the published production source for distributable artifacts. Warn loudly when building from a working source.
- **Explicit danger:** overwrites, promotions, restore operations, and version replacement need confirmation or explicit flags.
- **One canonical audio layer:** LineRecorder imports and whole-role splitting both converge into canonical segment audio; downstream commands should not branch by source path.
- **Automation ready:** every major status command should support `--format text|yaml|json`.

## Workspace And Production Context

The new CLI should resolve a `QuinceContext` before command execution.

Context includes:

- workspace root
- selected play id
- play directory
- build directory
- production source mode
- whether the play was inferred, configured, or explicitly selected

### Workspace Root Discovery

Root discovery should be deterministic and explainable.

Resolution order:

1. `--workspace <path>` if provided.
2. `QUINCE_WORKSPACE` environment variable if set.
3. Walk upward from the current directory looking for `quince.yaml`.
4. Walk upward looking for a directory containing `plays/` and either `play-config.yaml` or `pyproject.toml`.
5. If no root is found, fail with a short setup message.

`quince.yaml` is the preferred future workspace config. `play-config.yaml` remains supported for compatibility.

### Play Selection

Play selection should feel natural when managing several productions.

Resolution order:

1. `--play <play_id>` if provided.
2. If the current directory is inside `<workspace>/plays/<play_id>/`, infer that play.
3. If the current directory is inside `<workspace>/build/<play_id>/`, infer that play but note that this is generated output.
4. `active_play` in `quince.yaml`, if present.
5. `play_id` in existing `play-config.yaml`, if present.
6. If exactly one play directory exists under `plays/`, infer it.
7. Otherwise fail and list available play ids with examples.

Examples:

```sh
cd plays/androcles
quince status
```

should behave like:

```sh
quince status --play androcles
```

From the workspace root with multiple plays, this should fail clearly unless an active play is configured:

```text
Multiple productions found: androcles, hamlet, macbeth.
Run `quince status --play hamlet` or `quince use hamlet`.
```

### Active Play

`quince use <play_id>` should write the active play to workspace-local `quince.yaml`.

It should not write global user state. The active production is a property of the workspace, not the user account.

Example:

```yaml
version: 1
active_play: androcles
```

This keeps multi-production work predictable:

- running inside `plays/<play_id>/` overrides `active_play`;
- running at the workspace root uses `active_play`;
- `--play` overrides both.

## Producer Command Surface

The first screen should be short.

```sh
quince status
quince next
quince use <play_id>
quince list
quince publish
quince changes
quince cast
quince send-requests
quince receive-recordings <package.zip>
quince split-recordings
quince prepare-audio
quince build-playbook
quince build-audioplay
```

Advanced tools remain available through `./main` or an explicit expert namespace later.

### `quince status`

The primary dashboard.

It should show:

- selected workspace and play
- current published production version
- whether working `production.md` has unpublished changes
- cast assignment status
- missing/stale segment recordings
- missing whole-role source recordings
- blocking-only update counts
- cleanup review status
- voice-profile rendered-audio status
- Playbook version and freshness
- next recommended actions

Output formats:

```sh
quince status
quince status --format yaml
quince status --format json
```

### `quince next`

Print the next recommended action and why.

Examples:

```text
Next: publish
Reason: production.md has unpublished changes.
Command: quince publish --play androcles
```

`--run` may execute the recommended action only when it is non-destructive and unambiguous. Otherwise it should stop with the command to run.

### `quince list`

List productions under the workspace.

Suggested columns:

- play id
- title
- current published version
- working-change status
- Playbook freshness
- missing recording count

### `quince use <play_id>`

Set the workspace-local active play in `quince.yaml`.

It should validate that `plays/<play_id>/` exists and print the selected production title when available.

### `quince publish`

Producer-facing wrapper over production publication.

Default behavior:

- show `quince changes` summary first;
- prompt for a change summary if omitted and running interactively;
- reject reused changed ids unless the producer explicitly applies recommended id updates;
- clearly distinguish speech changes, blocking-only changes, and other context changes;
- offer to generate recording requests only for changes that need recording.

Examples:

```sh
quince publish --change-summary "Revised Act II entrance."
quince publish --recording-requests
```

### `quince changes`

Readable view of changes between working `production.md` and the current published version.

It should group changes by user impact:

- needs new recording
- blocking-only update
- context-only update
- added/removed script units
- id-reuse problems requiring producer decision

### `quince cast`

Cast config commands should be a small namespace:

```sh
quince cast show
quince cast check
quince cast assign <ROLE> <actor>
```

Editing `cast.yaml` directly remains supported. The CLI helpers exist to reduce YAML mistakes.

### `quince send-requests`

Build LineRecorder Recording Requests.

Default behavior should be conservative:

- if `cast.yaml` exists, use it to determine actor-facing metadata;
- skip roles configured as `recording: whole-role`;
- generate requests for missing or stale role segments when possible;
- support `--role`, `--actor`, `--changed-only`, and `--missing-only`;
- always print generated package paths.

Examples:

```sh
quince send-requests
quince send-requests --actor phil
quince send-requests --role MEGAERA --changed-only
```

### `quince receive-recordings <package.zip>`

Import a LineRecorder recording package.

It should:

- validate package/play/role/version metadata;
- import accepted takes;
- print the transaction path;
- immediately summarize remaining missing or stale recordings for that role.

### `quince split-recordings`

Producer-facing wrapper over whole-role splitting.

It should be described as an advanced workflow:

```sh
quince split-recordings --role ANDROCLES
```

It should only operate on roles configured as `recording: whole-role`, unless `--force-role-method` is supplied.

### `quince prepare-audio`

Guided audio readiness command.

It should report and optionally run safe steps:

- verify segment coverage;
- run cleanup analysis;
- render cleanup output;
- report cleanup review status;
- report voice-profile rendering status.

It should not promote cleaned audio automatically.

### `quince build-playbook`

Producer-facing Playbook builder.

It should:

- default to published production source;
- fail if required cue/response audio is missing;
- report production version, audio source, voice-profile use, and output path;
- warn when building from a working source.

### `quince build-audioplay`

Producer-facing audioplay builder.

It should mirror Playbook source-selection and audio-source behavior so producers do not need separate mental models for rehearsal and review outputs.

## Relationship To The Expert CLI

The expert CLI remains the complete toolbox.

Producer CLI commands should call shared services, not shell out to `./main` where avoidable. The implementation may initially delegate to existing command helper functions while service boundaries are cleaned up.

Suggested mapping:

| Producer command | Expert/Stager command |
| --- | --- |
| `quince status` | `./main production-status` |
| `quince publish` | `./main publish-production` |
| `quince changes` | `./main production-diff` |
| `quince send-requests` | `./main recording-request` |
| `quince receive-recordings` | `./main recording-import` |
| `quince split-recordings` | `./main segments` |
| `quince prepare-audio` | `./main verify`, `./main audio-cleanup ...`, `./main voice-render` |
| `quince build-playbook` | `./main playbook` |
| `quince build-audioplay` | `./main audioplay` |

## Help And Error Style

Help output should teach the workflow:

```text
Start with:
  quince status
  quince next

Common workflows:
  quince publish
  quince send-requests
  quince receive-recordings package.zip
  quince build-playbook
```

Errors should include:

- what went wrong;
- why it matters;
- the next command to try;
- relevant relative paths.

Example:

```text
No active production selected.

Found productions:
  androcles
  hamlet

Run:
  quince status --play androcles
  quince use androcles
```

## Future UI Compatibility

The producer CLI should be designed as the same workflow API a future local web UI or VS Code extension would use.

That means:

- status models should be structured dataclasses;
- commands should support JSON/YAML output where useful;
- command implementations should use service classes;
- text rendering should be separate from state collection.

