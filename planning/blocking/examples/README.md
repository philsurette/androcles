# Point-In-Time Staging Examples

These files mirror the exported staging overlay generated from inline notes in `production.md`. They remain useful as small renderer fixtures, but the normal workflow is to run `./block export` and render `build/<play_id>/staging/staging.txt`.

These examples use the current stage/set/scene syntax: stage geometry is top-level, reusable scenic setup lives inside `setup` blocks, set pieces use `piece`, and scene snapshots reference a setup with `set=<setup_id>`.

## Examples

- `text-only-stage.txt` starts with named zones and anchors. It does not require measured dimensions.
- `measured-stage.txt` uses exact `width`, `depth`, and coordinate anchors while preserving the same scene snapshot shape.
- `multi-level-stage.txt` adds a rectangular balcony level, an elevated anchor, and a stair connector.

## Rendering

Default portrait output, suitable for mobile viewing:

```sh
./block scene 1.2 planning/blocking/examples/text-only-stage.txt
```

Landscape output:

```sh
./block scene 1.3 planning/blocking/examples/multi-level-stage.txt \
  --orientation landscape
```

Stage-only output:

```sh
./block stage planning/blocking/examples/multi-level-stage.txt
```

Set-only output:

```sh
./block set act1 planning/blocking/examples/multi-level-stage.txt
```

Dimensions are optional. If a stage omits `width` and `depth`, the renderer uses a deterministic default proscenium stage so producers can start with rough named locations and add precision later.

Scene snapshots are authoritative point-in-time state. The renderer does not replay all previous blocking events to determine where actors and objects are; each rendered scene should provide the placements needed for that moment.

For staged progression inside a scene, use ordered `beat` blocks. Rendering with `--beat` starts from the scene snapshot and applies all beats for that scene up to the requested beat:

```sh
./block beat 1.3 b2 planning/blocking/examples/multi-level-stage.txt
```
