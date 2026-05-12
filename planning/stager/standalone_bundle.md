# Stager Standalone Bundle Plan

This note describes the first standalone Stager bundle shape for showrunners.

## Bundle Shape

The initial bundle is CLI-only:

```text
bundle-dist/stager
```

It includes:

- the Stager Python code,
- the Python runtime embedded by PyInstaller,
- Python package dependencies collected by PyInstaller,
- packaged Stager data such as `cue_window_presets.json`.

It intentionally does not include:

- `ffmpeg`,
- `ffprobe`,
- Audacity,
- Audacity project automation dependencies.

Stager audio commands already check for `ffmpeg` and `ffprobe` on `PATH` and print platform-specific install guidance when they are missing.

## Build

Install the bundle extra:

```sh
.venv/bin/python -m pip install -e '.[bundle]'
```

Build the executable:

```sh
./scripts/build_stager_bundle.sh --clean
```

Verify the bundle:

```sh
./bundle-dist/stager --help
./bundle-dist/stager scriptwright lock --help
./bundle-dist/stager playbook --help
```

## ffmpeg Policy

Do not bundle ffmpeg in the first standalone release.

Reasons:

- ffmpeg redistribution and licensing choices should be reviewed separately.
- Bundling ffmpeg increases bundle size.
- System ffmpeg is easier to update independently.
- The CLI can give clear missing-tool guidance before audio commands run.

Showrunners should install ffmpeg separately:

- macOS: `brew install ffmpeg`, or another trusted ffmpeg package.
- Windows: install ffmpeg and add its `bin` directory to `PATH`.
- Linux: use the system package manager.

## Distribution Notes

### macOS

Unsigned binaries may be blocked by Gatekeeper. A public release should decide whether to:

- distribute a zip with manual "open anyway" instructions,
- sign the executable with an Apple Developer ID,
- notarize the distribution.

Signing and notarization are not required for local testing, but they affect whether non-technical showrunners can launch the bundle without confusing warnings.

### Windows

Unsigned executables may trigger SmartScreen warnings. A public release should decide whether to:

- document the warning and manual override,
- code-sign releases,
- provide a conventional installer later.

### Linux

The first target is not a Linux app bundle. A later release can consider an AppImage or a documented wheel/pipx install path.

## Open Work

- Build and test the macOS executable outside the repository checkout.
- Test with a minimal sample play folder.
- Confirm Whisper-related dependencies are acceptable in bundle size.
- Decide whether the bundle should later grow a small GUI launcher for common workflows.
