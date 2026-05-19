#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/deploy_webapps_to_cloudflare.sh [--dry-run] [--skip-build] [--app cuemaster|linerecorder|all]

Build Cuemaster and/or LineRecorder as static web apps and deploy their dist/
folders to Cloudflare Pages using Wrangler direct upload.

Required environment for real deploys:
  CLOUDFLARE_API_TOKEN   API token with Pages deploy permission
  CLOUDFLARE_ACCOUNT_ID  Cloudflare account id used by Wrangler

Optional environment:
  CUEMASTER_PROJECT_NAME      Cloudflare Pages project name, default: cuemaster
  LINERECORDER_PROJECT_NAME   Cloudflare Pages project name, default: linerecorder

Options:
  --dry-run      Print planned actions without building or deploying.
  --skip-build   Deploy existing dist/ folders without running build:static.
  --app NAME     Deploy only cuemaster, only linerecorder, or all. Default: all.
EOF
}

dry_run=false
skip_build=false
app_filter="all"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      dry_run=true
      shift
      ;;
    --skip-build)
      skip_build=true
      shift
      ;;
    --app)
      app_filter="${2:?--app requires cuemaster, linerecorder, or all}"
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

case "$app_filter" in
  cuemaster|linerecorder|all) ;;
  *)
    echo "--app must be cuemaster, linerecorder, or all" >&2
    exit 2
    ;;
esac

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

run() {
  if [[ "$dry_run" == true ]]; then
    printf 'DRY RUN:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

require_env() {
  if [[ "$dry_run" == true ]]; then
    return
  fi
  if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
    echo "CLOUDFLARE_API_TOKEN is required for deployment." >&2
    exit 1
  fi
  if [[ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]]; then
    echo "CLOUDFLARE_ACCOUNT_ID is required for deployment." >&2
    exit 1
  fi
}

apps=()
if [[ "$app_filter" == "all" || "$app_filter" == "cuemaster" ]]; then
  apps+=(cuemaster)
fi
if [[ "$app_filter" == "all" || "$app_filter" == "linerecorder" ]]; then
  apps+=(linerecorder)
fi

project_name_for() {
  case "$1" in
    cuemaster)
      printf '%s\n' "${CUEMASTER_PROJECT_NAME:-cuemaster}"
      ;;
    linerecorder)
      printf '%s\n' "${LINERECORDER_PROJECT_NAME:-linerecorder}"
      ;;
  esac
}

require_env

for app in "${apps[@]}"; do
  if [[ "$skip_build" == false ]]; then
    echo "Building $app static bundle"
    run npm --prefix "$repo_root/$app" run build:static
  fi

  dist_dir="$repo_root/$app/dist"
  if [[ "$dry_run" == false && ! -d "$dist_dir" ]]; then
    echo "Build output not found: $dist_dir" >&2
    exit 1
  fi

  project_name="$(project_name_for "$app")"
  echo "Deploying $app/dist to Cloudflare Pages project $project_name"
  run npx wrangler pages deploy "$dist_dir" --project-name "$project_name"
done
