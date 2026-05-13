# Blocking Notes Manual Test

Use this checklist with the `fairies` play to verify the producer blocking workflow.

## 1. Parse The Working Production Source

```sh
PYTHONPATH=src .venv/bin/python -c "from pathlib import Path; from stager.scriptwright.production_script_parser import ProductionScriptParser; ProductionScriptParser(Path('plays/fairies/production.md')).parse_path(); print('ok')"
```

Expected:

- The command prints `ok`.
- No duplicate-id or explicit-blocking-id error appears.

## 2. Publish The Production Source

```sh
./main publish-production --play fairies
```

Expected:

- The command prints `Published production vNNNN.`
- The change report is shown.

## 3. Build Text Artifacts Without Blocking

```sh
./main text --play fairies -ps working
```

Expected:

- The full-play markdown file is `build/fairies/markdown/The_Curious_Case_of_the_Cottingley_Fairies.md`.
- Blocking text such as `settles beside the recorder`, `studies the photograph`, and `The room goes quiet` is not present.
- Visible line numbering has no gaps caused by hidden blocking.

## 4. Build Text Artifacts With Blocking

```sh
./main text --play fairies -ps working --blocking
```

Expected:

- The same markdown file includes standalone blocking lines.
- Role markdown includes blocking relevant to that role and wildcard `/*` blocking.
- Inline blocking appears only when `--blocking` is used.

## 5. Build A Playbook

```sh
./main playbook --play fairies -ps working
```

Expected:

- Playbook generation succeeds.
- Blocking is included in the Playbook manifest as actor/context information.
- Blocking does not require narrator audio.

## 6. Build A LineRecorder Recording Request

```sh
./main recording-request --play fairies --role LILLIAN -ps working
```

Expected:

- Recording Request generation succeeds.
- Relevant blocking appears in item context where applicable.
- Blocking does not create extra recording items.

## 7. Negative Test: Explicit Standalone Blocking Ids Are Invalid

Temporarily change a standalone blocking line to include an explicit id:

```md
- P-3 /LILLIAN: settles beside the recorder.
```

Then run:

```sh
PYTHONPATH=src .venv/bin/python -c "from pathlib import Path; from stager.scriptwright.production_script_parser import ProductionScriptParser; ProductionScriptParser(Path('plays/fairies/production.md')).parse_path()"
```

Expected:

- The command fails with `Standalone blocking entries must not use explicit production ids`.

Revert the temporary edit after this negative test.
