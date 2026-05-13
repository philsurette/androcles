# Production Publication Workflow

## Goal

Give the producer a simple loop:

1. Edit `plays/<play_id>/production.md`.
2. Run `./main publish-production --play <play_id>`.
3. Let Stager detect script changes, preserve history, recommend changed-line ids, and generate targeted Recording Requests.

The producer should not manually manage snapshots, diff sidecars, or per-role request item lists.

## Terms

- **Producer**: the person controlling `production.md`; this may be a stage manager, director, showrunner, or other production lead.
- **Producer source**: the editable `plays/<play_id>/production.md`.
- **Published production version**: Stager's managed snapshot of the producer source at a point in time.
- **Changed id reuse**: an existing production id appears in both versions but its normalized content fingerprint changed.

## Storage Layout

Stager manages production history under:

```text
build/<play_id>/production-history/
  current.json
  versions/
    v0001/
      production.md
      manifest.json
    v0002/
      production.md
      manifest.json
      changes_from_v0001.json
```

`current.json` identifies the current published version. The producer continues to edit only `plays/<play_id>/production.md`.

## Publish Flow

`./main publish-production` should:

1. Parse the current producer source.
2. If the source is draft production markdown, lock ids before publishing.
3. Load the last published version, if one exists.
4. Compare line ids and normalized content fingerprints.
5. Classify line changes:
   - `unchanged`
   - `changed_id_reuse`
   - `added`
   - `removed`
6. For each `changed_id_reuse`, recommend the next revision id, such as `2-5a`.
7. If requested, rewrite the producer source with the recommended revision ids before publishing.
8. Store the new published version.
9. Optionally generate Recording Requests for added and changed recordable role lines.

By default, changed id reuse should stop publication unless the producer applies recommended ids or explicitly allows id reuse. This protects existing recordings and Playbooks from silently treating changed text as the same line.

## Recording Requests

When publication includes Recording Requests, Stager should build one package per affected role.

Affected request items are:

- recordable segments under newly added role lines,
- recordable segments under revised role lines, after applying changed-id recommendations.

Each item should carry an item-level reason:

- `script_added`
- `script_changed`

This allows one role request to contain both added and changed material without losing why each item is present.

## Undo And Restore

`./main production-history` lists published versions.

`./main restore-production VERSION` copies a prior published `production.md` back to the producer source. It should not silently publish the restored file; the producer can inspect it and then run `publish-production` again.

Later, `restore-production --publish` can combine those steps.

## Initial Implementation Slice

- Add managed production history storage.
- Add diff classification against the current published version.
- Add recommended revision ids for changed id reuse.
- Add optional source rewrite for recommended ids.
- Add selected Recording Request generation for changed/added lines.
- Add CLI commands:
  - `publish-production`
  - `production-diff`
  - `production-history`
  - `restore-production`

## Later Work

- More sophisticated move detection.
- Interactive review UI for all recommended id updates.
- Automatic inserted-line id suggestions for newly inserted draft lines.
- Report output formats suitable for email or rehearsal notes.
- Build commands that explicitly consume the current published snapshot instead of the editable source.
