# Point-In-Time Staging Examples

These files are standalone inputs for the current `stager.staging.render_point` spike. They are intentionally decoupled from `production.md`, Playbook generation, and Cuemaster.

## Examples

- `text-only-stage.txt` starts with named zones and anchors. It does not require measured dimensions.
- `measured-stage.txt` uses exact `width`, `depth`, and coordinate anchors while preserving the same scene snapshot shape.
- `multi-level-stage.txt` adds a rectangular balcony level, an elevated anchor, and a stair connector.

## Rendering

Default portrait output, suitable for mobile viewing:

```sh
PYTHONPATH=src .venv/bin/python -m stager.staging.render_point \
  planning/blocking/examples/text-only-stage.txt \
  --scene 1.2 \
  --out /tmp/text-only-stage.svg
```

Landscape output:

```sh
PYTHONPATH=src .venv/bin/python -m stager.staging.render_point \
  planning/blocking/examples/multi-level-stage.txt \
  --scene 1.3 \
  --out /tmp/multi-level-stage-landscape.svg \
  --orientation landscape
```

Dimensions are optional. If a stage omits `width` and `depth`, the renderer uses a deterministic default proscenium stage so producers can start with rough named locations and add precision later.

Scene snapshots are authoritative point-in-time state. The renderer does not replay all previous blocking events to determine where actors and objects are; each rendered scene should provide the placements needed for that moment.

For staged progression inside a scene, use ordered `beat` blocks. Rendering with `--beat` starts from the scene snapshot and applies all beats for that scene up to the requested beat:

```sh
PYTHONPATH=src .venv/bin/python -m stager.staging.render_point \
  planning/blocking/examples/multi-level-stage.txt \
  --scene 1.3 \
  --beat b2 \
  --out /tmp/multi-level-stage-b2.svg
```
