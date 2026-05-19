# Point-In-Time Staging Examples

These files are standalone inputs for the `./block` CLI. They are intentionally decoupled from `production.md`, Playbook generation, and Cuemaster.

These examples use the current stage/set/scene syntax: stage geometry is top-level, reusable scenic setup lives inside `setup` blocks, set pieces use `piece`, and scene snapshots reference a setup with `set=<setup_id>`.

## Examples

- `text-only-stage.txt` starts with named zones and anchors. It does not require measured dimensions.
- `measured-stage.txt` uses exact `width`, `depth`, and coordinate anchors while preserving the same scene snapshot shape.
- `multi-level-stage.txt` adds a rectangular balcony level, an elevated anchor, and a stair connector.

## Rendering

Default portrait output, suitable for mobile viewing:

```sh
./block scene \
  planning/blocking/examples/text-only-stage.txt \
  --scene 1.2 \
  --out /tmp/text-only-stage.svg
```

Landscape output:

```sh
./block scene \
  planning/blocking/examples/multi-level-stage.txt \
  --scene 1.3 \
  --out /tmp/multi-level-stage-landscape.svg \
  --orientation landscape
```

Stage-only output:

```sh
./block stage \
  planning/blocking/examples/multi-level-stage.txt \
  --out /tmp/multi-level-stage.svg
```

Set-only output:

```sh
./block set \
  planning/blocking/examples/multi-level-stage.txt \
  --set act1 \
  --out /tmp/multi-level-stage-set.svg
```

Dimensions are optional. If a stage omits `width` and `depth`, the renderer uses a deterministic default proscenium stage so producers can start with rough named locations and add precision later.

Scene snapshots are authoritative point-in-time state. The renderer does not replay all previous blocking events to determine where actors and objects are; each rendered scene should provide the placements needed for that moment.

For staged progression inside a scene, use ordered `beat` blocks. Rendering with `--beat` starts from the scene snapshot and applies all beats for that scene up to the requested beat:

```sh
./block beat \
  planning/blocking/examples/multi-level-stage.txt \
  --scene 1.3 \
  --beat b2 \
  --out /tmp/multi-level-stage-b2.svg
```
