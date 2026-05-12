#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/build_stager_bundle.sh [--clean]

Build a CLI-only Stager executable with PyInstaller.

The bundle intentionally does not include ffmpeg or ffprobe. Install those
separately and keep them on PATH for Stager audio commands.

Options:
  --clean  Remove PyInstaller work/dist output before building.
EOF
}

clean=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --clean)
      clean=true
      shift
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
spec_path="$repo_root/packaging/stager.spec"
work_path="$repo_root/bundle-build"
dist_path="$repo_root/bundle-dist"

if ! "$repo_root/.venv/bin/python" -c "import PyInstaller" >/dev/null 2>&1; then
  cat >&2 <<'EOF'
PyInstaller is not installed in .venv.

Install the bundle extra first:

  .venv/bin/python -m pip install -e '.[bundle]'

EOF
  exit 1
fi

if [[ "$clean" == true ]]; then
  rm -rf "$work_path" "$dist_path"
fi

"$repo_root/.venv/bin/python" -m PyInstaller \
  --noconfirm \
  --clean \
  --workpath "$work_path" \
  --distpath "$dist_path" \
  "$spec_path"

cat <<EOF

Built Stager bundle:
  $dist_path/stager

Verify with:
  $dist_path/stager --help
  $dist_path/stager playbook --help
EOF
