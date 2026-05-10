# Missing Audio Policy

This document defines when Stager should fail on missing audio.

## Principle

User-consumable outputs should be complete by construction. If required audio is missing, Stager should raise an exception rather than logging a warning, emitting silence, or writing placeholder metadata.

Diagnostic commands may keep explicit opt-in behavior for inspecting incomplete projects.

## Required Audio

Required for Cuemaster Playbooks:

- Cue audio for every rehearsable non-meta role line.
- Response audio for every rehearsable non-meta role line.
- Narrator audio when narrator/direction text is used as a cue.

Required when the corresponding feature is enabled:

- Caller/callout audio when callouts are enabled as required output.
- Announcer audio for generated announcer tracks.
- Librivox preamble and epilog snippets when Librivox output is enabled.

## Optional Or Diagnostic Audio

The following may remain optional only behind an explicit diagnostic mode:

- timing previews for incomplete recordings
- build previews that intentionally show missing segment gaps
- developer-only reports that list missing files

The proposed CLI spelling is `--allow-missing-audio`, but it should only be added to commands that need diagnostic behavior.

## Error Style

Missing required audio should raise `RuntimeError` or a narrower project exception if one is introduced.

Messages should include:

- role id
- segment id or block id
- expected file path formatted with `paths.display_path()`
- output being generated, such as `Playbook`, `cue file`, or `audioplay`

Example:

```text
Missing required response audio for role MEGAERA segment 0_5_2 while building Playbook: build/androcles/audio/segments/MEGAERA/0_5_2.wav
```

## Current Compatibility

Existing Stager outputs may temporarily keep diagnostic missing-audio behavior while Playbook generation is introduced. Do not copy that behavior into Playbook code.

When changing an existing command from permissive to strict, add a test and document any compatibility flag.

