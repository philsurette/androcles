#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/deploy_webapps_to_cloudflare.sh [--dry-run] [--skip-build] [--force] [--app cuemaster|linerecorder|all] [--env-file PATH]

Build Cuemaster and/or LineRecorder as static web apps and deploy their dist/
folders to Cloudflare Pages using Wrangler direct upload.

Credentials are read from a local env file. The default path is:
  ~/.config/quince/cloudflare-deploy.env

Required env-file variables:
  CLOUDFLARE_API_TOKEN   API token with Pages deploy permission
  CLOUDFLARE_ACCOUNT_ID  Cloudflare account id used by Wrangler

Optional env-file variables:
  CUEMASTER_PROJECT_NAME      Cloudflare Pages project name, default: cuemaster
  LINERECORDER_PROJECT_NAME   Cloudflare Pages project name, default: linerecorder

Options:
  --dry-run        Print planned actions without building, deploying, or saving deploy state.
  --skip-build     Deploy existing dist/ folders without running build:static.
  --force          Deploy even if the local artifact hash matches the last successful deployment.
  --app NAME       Deploy only cuemaster, only linerecorder, or all. Default: all.
  --env-file PATH  Credential file path. Default: ~/.config/quince/cloudflare-deploy.env.

Example env file:
  CLOUDFLARE_ACCOUNT_ID=...
  CLOUDFLARE_API_TOKEN=...
  CUEMASTER_PROJECT_NAME=cuemaster
  LINERECORDER_PROJECT_NAME=linerecorder
EOF
}

dry_run=false
skip_build=false
force=false
app_filter="all"
env_file="${HOME}/.config/quince/cloudflare-deploy.env"

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
    --force)
      force=true
      shift
      ;;
    --app)
      app_filter="${2:?--app requires cuemaster, linerecorder, or all}"
      shift 2
      ;;
    --env-file)
      env_file="${2:?--env-file requires a path}"
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
deploy_state_dir="$repo_root/.deploy/cloudflare"

run() {
  if [[ "$dry_run" == true ]]; then
    printf 'DRY RUN:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

load_env_file() {
  if [[ "$dry_run" == true && ! -e "$env_file" ]]; then
    return
  fi
  if [[ ! -f "$env_file" ]]; then
    echo "Cloudflare deploy env file not found: $env_file" >&2
    echo "Create it with CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN, then chmod 600 it." >&2
    exit 1
  fi
  require_private_file "$env_file"
  set -a
  # shellcheck disable=SC1090
  source "$env_file"
  set +a
}

require_private_file() {
  local path="$1"
  local mode
  mode="$(file_mode "$path")"
  case "$mode" in
    600|400) ;;
    *)
      echo "Refusing to read $path because its permissions are $mode; expected 600 or 400." >&2
      echo "Run: chmod 600 $path" >&2
      exit 1
      ;;
  esac
}

file_mode() {
  local path="$1"
  if stat -f '%Lp' "$path" >/dev/null 2>&1; then
    stat -f '%Lp' "$path"
  else
    stat -c '%a' "$path"
  fi
}

require_env() {
  if [[ "$dry_run" == true ]]; then
    return
  fi
  if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
    echo "CLOUDFLARE_API_TOKEN is required in $env_file." >&2
    exit 1
  fi
  if [[ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]]; then
    echo "CLOUDFLARE_ACCOUNT_ID is required in $env_file." >&2
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

dist_hash() {
  local dist_dir="$1"
  (
    cd "$dist_dir"
    find . -type f -print0 \
      | sort -z \
      | xargs -0 shasum -a 256 \
      | shasum -a 256 \
      | awk '{print $1}'
  )
}

state_file_for() {
  local app="$1"
  local project_name="$2"
  printf '%s/%s-%s.sha256\n' "$deploy_state_dir" "$app" "$project_name"
}

load_env_file
require_env

deployed_count=0
skipped_count=0

for app in "${apps[@]}"; do
  if [[ "$skip_build" == false ]]; then
    echo "Building $app static bundle"
    run npm --prefix "$repo_root/$app" run build:static
  fi

  dist_dir="$repo_root/$app/dist"
  if [[ ! -d "$dist_dir" ]]; then
    echo "Build output not found: $dist_dir" >&2
    exit 1
  fi

  project_name="$(project_name_for "$app")"
  current_hash="$(dist_hash "$dist_dir")"
  state_file="$(state_file_for "$app" "$project_name")"
  previous_hash=""
  if [[ -f "$state_file" ]]; then
    previous_hash="$(tr -d '[:space:]' < "$state_file")"
  fi

  if [[ "$force" == false && "$current_hash" == "$previous_hash" ]]; then
    echo "Skipping $app: dist hash matches last successful deploy for Cloudflare Pages project $project_name."
    skipped_count=$((skipped_count + 1))
    continue
  fi

  echo "Deploying $app/dist to Cloudflare Pages project $project_name"
  echo "Artifact hash: $current_hash"
  run npx wrangler pages deploy "$dist_dir" --project-name "$project_name"

  if [[ "$dry_run" == false ]]; then
    mkdir -p "$deploy_state_dir"
    printf '%s\n' "$current_hash" > "$state_file"
  fi
  deployed_count=$((deployed_count + 1))
done

if [[ "$deployed_count" -eq 0 && "$skipped_count" -gt 0 ]]; then
  echo "No Cloudflare deployment was created because selected artifacts are unchanged. Use --force to deploy anyway."
fi
