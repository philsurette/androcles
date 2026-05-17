# Quince Versioning Design

This document defines versioning rules for Quince exchange formats and production manuscript releases. It is the source of truth for compatibility behavior; individual manifest specs should link here rather than redefining these rules.

## Scope

This design covers:

- Playbook package/manifest format versions consumed by Cuemaster.
- Recording package format versions consumed by LineRecorder and Stager.
- Production manuscript versions for `production.md` publication history.
- How production manuscript versions are carried into Playbooks and Recording Requests.

This document does not define production id syntax or content hashing. Those remain in [production_script_ids.md](production_script_ids.md).

## Terms

- **Format version**: The version of a machine-readable package contract, such as a Playbook manifest or recording manifest.
- **Production version**: The structured publication identity of the script/manuscript content in `plays/<play_id>/production.md`.
- **Build id**: A unique id for one generated artifact build. Two Playbooks can have different build ids while using the same production version.
- **Content hash**: A normalized fingerprint for one line or segment, used to detect changed text behind a reused production id.

## Format Versioning

Playbooks and recording packages should use semantic format versions:

```json
{
  "format_version": "1.0.0"
}
```

The existing numeric `schema_version` field remains valid during migration. New package writers should emit both fields until all consumers have moved to `format_version`:

```json
{
  "schema_version": 1,
  "format_version": "1.0.0"
}
```

During this migration, `schema_version: 1` means `format_version: 1.0.0` when `format_version` is absent.

### Version Parts

- **Major** changes are breaking. Consumers that support major version `1` must reject major version `2`.
- **Minor** changes are backward-compatible additions. Consumers that support `1.2.0` may read `1.3.0`, but should warn that the package was produced by a newer format.
- **Patch** changes are documentation clarifications, validation tightening that rejects already-invalid packages, writer bug fixes, or equivalent non-shape changes. Consumers should read newer patch versions without warning.

Consumers should compare only the format version, not the Stager app version, LineRecorder app version, or Cuemaster app version.

## Breaking Changes

A format change is breaking when an existing correct consumer could misread the package or fail to provide the promised behavior.

Breaking changes require a major version increment. Examples:

- Removing a required field.
- Renaming a field.
- Changing a field's type.
- Changing the meaning or units of an existing field, such as milliseconds to seconds.
- Changing path resolution rules.
- Changing id semantics, such as making `id` stop meaning production id.
- Making a previously optional field required for basic use.
- Changing package layout in a way older consumers cannot locate required files.
- Changing role, line, cue, response, or recording ordering semantics.
- Replacing strict required-audio behavior with optional or fallback behavior for the same field.

For now, Cuemaster and LineRecorder should not attempt compatibility shims across breaking major versions. They should reject the package with a clear user-facing message.

## Backward-Compatible Changes

A format change is backward-compatible when an older correct consumer can ignore the new data and still provide the behavior promised by the older format.

Backward-compatible changes require a minor version increment. Examples:

- Adding optional fields.
- Adding optional arrays or objects.
- Adding advisory metadata that does not change interpretation of existing fields.
- Adding new enum values only when older consumers can safely ignore the containing feature.
- Adding optional assets that are not required for the older behavior.
- Adding richer diagnostics, provenance, or display hints.

Patch changes do not require a consumer warning. Examples:

- Clarifying prose in a spec.
- Fixing examples.
- Tightening validation for packages that were already invalid.
- Fixing writer behavior without changing the accepted contract.

## Consumer Behavior

Each consumer should declare the newest format version it fully understands for each package type.

When reading a package:

1. If `format_version` is present, parse it as semantic version.
2. If `format_version` is absent and `schema_version` is present, map known numeric schema versions to semantic versions.
3. If no known version field is present, reject the package.
4. If the package major version is greater than the supported major version, reject it.
5. If the package major version is lower than the supported major version, reject it unless an explicit compatibility importer exists.
6. If the package minor version is greater than the supported minor version for the same major, read it and show a warning.
7. If only the patch version is greater, read it without warning.

Cuemaster behavior for Playbooks:

- Reject newer major versions.
- Reject older major versions unless a deliberate importer is implemented.
- Read newer minor versions with a warning that some newer Playbook features may not be shown or used.
- Read newer patch versions without warning.

LineRecorder behavior for Recording Request packages:

- Reject newer major versions.
- Reject older major versions unless a deliberate importer is implemented.
- Read newer minor versions with a warning that some request metadata may be ignored.
- Read newer patch versions without warning.

Stager behavior for LineRecorder recording export packages:

- Reject newer major versions.
- Reject older major versions unless a deliberate importer is implemented.
- Read newer minor versions with a warning and preserve known fields only.
- Read newer patch versions without warning.

For all consumers, unsupported-version errors should name the package version and the newest supported version.

## Playbook Format Version

The Playbook manifest should include:

```json
{
  "schema_version": 1,
  "format_version": "1.0.0",
  "package_type": "playbook"
}
```

`package_type` is recommended even if the zip layout already implies the type. It gives consumers a cheap validation point and makes future tooling clearer.

The current Playbook v1 contract is defined by [playbook_manifest.md](playbook_manifest.md). Initial implementation may continue to read `schema_version: 1` as v1.0.0.

## Recording Format Versions

There are two recording package types:

- `recording_request`: Stager or Cuemaster to LineRecorder. This is the work order an actor records from.
- `role_recordings`: LineRecorder to Stager. This is the actor's recording export package.

They share the recording manifest versioning policy but are different package directions with different payload shapes.

Recording Request manifests should include:

```json
{
  "schema_version": 1,
  "format_version": "1.0.0",
  "package_type": "recording_request"
}
```

LineRecorder recording export package manifests should include:

```json
{
  "schema_version": 1,
  "format_version": "1.0.0",
  "package_type": "role_recordings"
}
```

The current recording contracts are defined by [recording_package_manifest.md](recording_package_manifest.md). Initial implementation may continue to read `schema_version: 1` as v1.0.0.

## Production Manuscript Versions

`production.md` should carry a structured production version in its metadata header:

```text
// script_format: quince-production-v1
// source_kind: production
// production_ids: locked
// production_version: 7@k9f4p2x8m1qd
// parent_production_version: 6@h7p2v9c4t6ra
```

The production version identifies a published manuscript snapshot, not a file format. It should change only when the producer publishes a version, not on every edit or artifact build.

### Production Version Shape

Production versions should have two parts:

```text
<sequence>@<publication-id>
```

Example:

```text
7@k9f4p2x8m1qd
```

Fields:

- `sequence`: A monotonically increasing positive integer within one production lineage.
- `publication-id`: An immutable unique id for this publication event.

The publication id should be generated by Stager when publishing. It should be a short random id with enough entropy to make accidental collisions negligible in local production workflows. A good default is a 12-character Crockford Base32 or lowercase Base32 token generated from at least 60 random bits, such as `k9f4p2x8m1qd`. Eight hex characters is too short because it only carries 32 bits of entropy. A full UUID, UUIDv7, or ULID is also acceptable internally, but the manuscript-facing id should be short enough for humans to compare and type when needed.

Publication time should be stored separately as `published_at`. Do not rely on timestamps for uniqueness; two producers can publish from separate machines at nearly the same time, and clocks can be wrong.

The sequence is human-facing and convenient. The full `sequence@publication-id` is the actual identity.

This document calls the manuscript counter `sequence` rather than `major` to avoid confusion with semantic format-version major numbers. It serves the same purpose as the producer-facing monotonically increasing manuscript version number.

### Fork Detection

A fork exists when two production manuscripts claim the same sequence number but have different publication ids.

Example fork:

```text
7@k9f4p2x8m1qd
7@z8n3d5q1w6te
```

This means two producers probably started from the same prior version and independently published "version 7". Stager should detect and report this instead of treating one as a normal successor of the other.

`parent_production_version` should record the full production version from which the new version was published. It lets Stager distinguish a normal successor from a divergent branch:

- Normal successor: `sequence` is parent sequence + 1, and `parent_production_version` equals the current published version.
- Fork: `sequence` collides with an existing version but `publication-id` differs.
- Out-of-date publish attempt: parent version is not the current published version.
- Unknown lineage: `parent_production_version` is missing or does not exist in local history.

When Stager sees a fork or out-of-date publish attempt, it should stop publication and ask the producer to merge or intentionally publish a new successor version.

### Version Source Of Truth

The managed publication history remains authoritative:

```text
build/<play_id>/production-history/current.json
build/<play_id>/production-history/versions/0007-k9f4p2x8m1qd/production.md
```

The `production_version` metadata in the working `plays/<play_id>/production.md` is a convenience mirror of the latest published version when the working file matches that published snapshot.

### Publish Behavior

`./main publish-production` should:

1. Parse the working `production.md`.
2. Diff it against the current published version when one exists.
3. Reject changed id reuse unless ids are updated or the user explicitly allows reuse.
4. Verify `parent_production_version` is either absent for the first publication or matches the current published version.
5. Allocate the next sequence number.
6. Generate a new publication id.
7. Write `production_version` and `parent_production_version` into the published snapshot.
8. Update the working `production.md` with those fields after successful publication.
9. Store publication metadata under `production-history`.

If the working `production.md` has unmerged differences from the current published version, Stager should treat its `production_version` metadata as stale. It may either remove the field during rewrite or replace it only after publication succeeds. It should not let a stale `production_version` imply that unpublished edits are already published.

### Back-Writing Versions

Back-writing production versions into `production.md` is allowed only from publication commands. Normal build commands should not mutate the manuscript.

When `production-diff` detects differences between the working file and the current published snapshot, it should report:

- the current published production version,
- whether the working file metadata matches that version,
- whether the working file has unpublished changes.

It should not silently increment or rewrite `production_version`.

## Artifact Production Metadata

Playbooks should include the production version they were built from:

```json
{
  "production": {
    "version": "7@k9f4p2x8m1qd",
    "sequence": 7,
    "publication_id": "k9f4p2x8m1qd",
    "parent_version": "6@h7p2v9c4t6ra",
    "source": "published",
    "published_at": "2026-05-17T13:40:00Z"
  }
}
```

Recording Requests should include the production version they were created from:

```json
{
  "request": {
    "id": "androcles-MEGAERA-7-k9f4p2x8m1qd-selected-2026-05-17",
    "kind": "selected_segments",
    "created_at": "2026-05-17T13:45:00Z",
    "created_by": "stager",
    "production_version": "7@k9f4p2x8m1qd"
  },
  "play": {
    "id": "androcles",
    "title": "Androcles and the Lion",
    "version": "7@k9f4p2x8m1qd"
  }
}
```

LineRecorder recording export packages should preserve the originating request's production version:

```json
{
  "request": {
    "id": "androcles-MEGAERA-7-k9f4p2x8m1qd-selected-2026-05-17",
    "production_version": "7@k9f4p2x8m1qd"
  },
  "play": {
    "id": "androcles",
    "version": "7@k9f4p2x8m1qd"
  }
}
```

Stager import should compare the package production version to the target published production version and report mismatches. The content hashes remain the decisive stale-recording check because a production version mismatch can still contain unchanged segments.

## Build Source Rules

When a command can produce actor-facing artifacts, it should record which production source was used:

- `source: "published"` when built from the current published snapshot.
- `source: "working"` when built from the editable working `production.md`.

Release/distribution workflows should prefer published sources. Working-source builds are useful for previews but should be visibly marked so they are not mistaken for release artifacts.

## Migration Plan

1. Add this document and link it from manifest specs.
2. Add `format_version: "1.0.0"` and `package_type` to Playbook and recording package writers while preserving `schema_version: 1`.
3. Add consumer version checks using the rules above.
4. Add structured `production_version` and `parent_production_version` to publication snapshots and back-write them to working `production.md` only after successful publication.
5. Include production metadata in Playbooks and Recording Requests.
6. Preserve request production metadata in LineRecorder recording export packages.
7. Add tests for newer minor warnings, newer major rejection, missing version rejection, and production-version propagation.

## Open Questions

- Should unpublished working builds use a synthetic version such as `7@k9f4p2x8m1qd+working.20260517T134500Z`, or should they omit `production.version` and rely on `source: "working"` plus build metadata?
- Should LineRecorder recording export package import reject production-version mismatches by default, or warn and rely on content hashes?
- Should `production_version` metadata be required in locked `production.md` after publication history exists, or remain optional for unpublished plays?
