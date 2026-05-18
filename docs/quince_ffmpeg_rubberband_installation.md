## Installing Optional FFmpeg Rubber Band Support On macOS

Quince uses FFmpeg for audio processing, but Quince must work with a normal LGPL-compatible FFmpeg installation. Rubber Band support is optional.

The important licensing boundary is:

- Quince does not bundle FFmpeg.
- Quince does not require GPL-enabled FFmpeg.
- Quince's required audio features must work with the normal FFmpeg package.
- If a user separately installs a GPL-enabled FFmpeg build that includes the `rubberband` filter, Quince may detect and use it for optional higher-quality pitch shifting.

On macOS, Homebrew's normal `ffmpeg` package is the baseline install. Homebrew's `ffmpeg-full` package can include Rubber Band support, but it is GPL-enabled because it is built with GPL options such as `--enable-gpl`, and Rubber Band itself is GPL-licensed. Treat `ffmpeg-full` as an optional user-managed enhancement, not a Quince dependency.

### 1. Install Homebrew

If Homebrew is not already installed, install it from:

https://brew.sh/

After installing Homebrew, restart Terminal or follow Homebrew's shell setup instructions.

### 2. Install baseline FFmpeg

For normal Quince use, install the standard FFmpeg package:

```bash
brew update
brew install ffmpeg
```

Verify:

```bash
ffmpeg -version
ffprobe -version
```

This baseline install should be enough for Quince's required FFmpeg integration.

### 3. Optional: install GPL-enabled `ffmpeg-full` for Rubber Band

```bash
brew update
brew install ffmpeg-full
```

This may take a while. FFmpeg has many audio/video codec dependencies. If Homebrew uses prebuilt bottles for your system, installation is usually much faster than building from source.

Only install `ffmpeg-full` if you specifically want optional Rubber Band pitch-shifting support and are comfortable using a GPL-enabled FFmpeg build on your own machine.

### 4. Verify Rubber Band support

Run:

```bash
$(brew --prefix ffmpeg-full)/bin/ffmpeg -hide_banner -filters | grep rubberband
```

You should see a line similar to:

```text
.. rubberband        A->A       Apply time-stretching and pitch-shifting.
```

You can also inspect the filter directly:

```bash
$(brew --prefix ffmpeg-full)/bin/ffmpeg -hide_banner -h filter=rubberband
```

If this command prints help for the `rubberband` filter, the installation is ready for Quince.

### 5. Create the Quince FFmpeg config file

Quince does not require the optional GPL-enabled FFmpeg to be available globally on your shell `PATH`. Instead, Quince can read an `ffmpeg.conf` file that stores the FFmpeg binary directory. This lets you keep standard `ffmpeg` as your default shell command while allowing Quince to use `ffmpeg-full` only when you explicitly configure it.

From the Quince project folder, run:

```bash
mkdir -p .quince
printf "ffmpeg_bin_dir=%s\n" "$(brew --prefix ffmpeg-full)/bin" > .quince/ffmpeg.conf
```

This creates:

```text
.quince/ffmpeg.conf
```

with content similar to:

```text
ffmpeg_bin_dir=/usr/local/opt/ffmpeg-full/bin
```

or, on Apple Silicon Macs:

```text
ffmpeg_bin_dir=/opt/homebrew/opt/ffmpeg-full/bin
```

Quince should use this directory when constructing FFmpeg-related command paths, for example:

```text
<ffmpeg_bin_dir>/ffmpeg
<ffmpeg_bin_dir>/ffprobe
```

### 6. Verify the config file

Run:

```bash
cat .quince/ffmpeg.conf
```

Then test the configured FFmpeg path:

```bash
FFMPEG_BIN_DIR="$(sed -n 's/^ffmpeg_bin_dir=//p' .quince/ffmpeg.conf)"
"$FFMPEG_BIN_DIR/ffmpeg" -hide_banner -h filter=rubberband
```

If the second command shows Rubber Band filter help, Quince should be able to use the optional installed FFmpeg build for Rubber Band features.

### Troubleshooting

#### `rubberband` is not found

If this fails:

```bash
$(brew --prefix ffmpeg-full)/bin/ffmpeg -hide_banner -h filter=rubberband
```

try reinstalling:

```bash
brew update
brew reinstall ffmpeg-full
```

Then test again.

#### The regular `ffmpeg` command does not show Rubber Band support

This is expected and acceptable. The standard `ffmpeg` package should not be expected to include the Rubber Band filter.

Use the `ffmpeg-full` path instead:

```bash
$(brew --prefix ffmpeg-full)/bin/ffmpeg
```

Quince should rely on the path written to `.quince/ffmpeg.conf` for optional Rubber Band features, not on whichever `ffmpeg` happens to appear first on the user's shell `PATH`.

#### `ffmpeg-full` and `ffmpeg` are both installed

That is okay. They can coexist. Quince's required features should work with the normal `ffmpeg` install. Optional Rubber Band features can use the `ffmpeg-full` binary directory when configured.

To see both installations:

```bash
brew list --versions ffmpeg ffmpeg-full
```

To check which plain `ffmpeg` your shell would run:

```bash
which ffmpeg
ffmpeg -version
```

This does not affect optional Rubber Band use if `.quince/ffmpeg.conf` points to the `ffmpeg-full` binary directory.

### Licensing note

Rubber Band is licensed under GPL-2.0-or-later. Homebrew's `ffmpeg-full` formula is GPL-3.0-or-later because it is built with GPL-enabled FFmpeg options. Quince must not bundle FFmpeg, Rubber Band, or `ffmpeg-full`, and Quince must not make GPL-enabled FFmpeg a required dependency.

The intended integration model is user-provided tooling:

- Required Quince FFmpeg workflows use the standard FFmpeg install.
- Optional Rubber Band workflows are enabled only when the user's configured FFmpeg binary provides the `rubberband` filter.
- If Rubber Band is unavailable, Quince should fall back to portable FFmpeg pitch shifting or disable only the optional higher-quality pitch mode.

### Optional global config location

The examples above use a project-local config file:

```text
.quince/ffmpeg.conf
```

For a global Quince setting, use:

```bash
mkdir -p "$HOME/.config/quince"
printf "ffmpeg_bin_dir=%s\n" "$(brew --prefix ffmpeg-full)/bin" > "$HOME/.config/quince/ffmpeg.conf"
```
