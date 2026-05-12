#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/publish_webapps_to_pages.sh [--dry-run] [--pages-dir PATH]

Build Cuemaster and LineRecorder as static web apps and publish them into a
sibling GitHub Pages checkout.

Options:
  --dry-run         Print planned actions without building, deleting, or copying.
  --pages-dir PATH  GitHub Pages checkout. Default: ../philsurette.github.io
EOF
}

dry_run=false
pages_dir="../philsurette.github.io"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      dry_run=true
      shift
      ;;
    --pages-dir)
      pages_dir="${2:?--pages-dir requires a path}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pages_root="$(cd "$repo_root" && mkdir -p "$(dirname "$pages_dir")" && cd "$pages_dir" && pwd)"

apps=(cuemaster linerecorder)

run() {
  if [[ "$dry_run" == true ]]; then
    printf 'DRY RUN:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

require_pages_repo() {
  if [[ ! -d "$pages_root/.git" ]]; then
    echo "Expected a Git checkout at $pages_root" >&2
    exit 1
  fi
}

require_clean_target() {
  local app="$1"
  local target="$pages_root/$app"
  local relative_target="$app"

  if [[ ! -e "$target" ]]; then
    return
  fi

  if ! git -C "$pages_root" diff --quiet -- "$relative_target"; then
    echo "Refusing to publish because $relative_target has unstaged changes in $pages_root" >&2
    exit 1
  fi

  if ! git -C "$pages_root" diff --cached --quiet -- "$relative_target"; then
    echo "Refusing to publish because $relative_target has staged changes in $pages_root" >&2
    exit 1
  fi
}

build_app() {
  local app="$1"
  echo "Building $app"
  run npm --prefix "$repo_root/$app" run build:static
}

publish_app() {
  local app="$1"
  local source="$repo_root/$app/dist"
  local target="$pages_root/$app"

  if [[ "$dry_run" == false && ! -d "$source" ]]; then
    echo "Build output not found: $source" >&2
    exit 1
  fi

  echo "Publishing $app to $target"
  run rm -rf "$target"
  run mkdir -p "$target"
  run cp -R "$source/." "$target/"
}

require_pages_repo

for app in "${apps[@]}"; do
  require_clean_target "$app"
done

for app in "${apps[@]}"; do
  build_app "$app"
  publish_app "$app"
done

cat <<EOF

Published web apps to:
  $pages_root/cuemaster/
  $pages_root/linerecorder/

Review and commit the GitHub Pages repo separately:
  git -C "$pages_root" status --short
EOF
