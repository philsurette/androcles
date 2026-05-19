#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
temp_dir="$(mktemp -d)"
trap 'rm -rf "$temp_dir"' EXIT

env_file="$temp_dir/cloudflare-deploy.env"
cat > "$env_file" <<'EOF'
CLOUDFLARE_ACCOUNT_ID=test-account
CLOUDFLARE_API_TOKEN=test-token
CUEMASTER_PROJECT_NAME=test-cuemaster
EOF
chmod 600 "$env_file"

mkdir -p "$repo_root/cuemaster/dist"
printf 'hello\n' > "$repo_root/cuemaster/dist/index.html"
rm -f "$repo_root/.deploy/cloudflare/cuemaster-test-cuemaster.sha256"

output_first="$(
  "$repo_root/scripts/deploy_webapps_to_cloudflare.sh" \
    --dry-run \
    --skip-build \
    --app cuemaster \
    --env-file "$env_file"
)"

if [[ "$output_first" != *"wrangler pages deploy"* ]]; then
  echo "Expected dry run to plan a Wrangler deployment" >&2
  echo "$output_first" >&2
  exit 1
fi

mkdir -p "$repo_root/.deploy/cloudflare"
hash_value="$(
  cd "$repo_root/cuemaster/dist"
  find . -type f -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256 | awk '{print $1}'
)"
printf '%s\n' "$hash_value" > "$repo_root/.deploy/cloudflare/cuemaster-test-cuemaster.sha256"

output_second="$(
  "$repo_root/scripts/deploy_webapps_to_cloudflare.sh" \
    --dry-run \
    --skip-build \
    --app cuemaster \
    --env-file "$env_file"
)"

if [[ "$output_second" != *"Skipping cuemaster"* ]]; then
  echo "Expected matching artifact hash to skip deployment" >&2
  echo "$output_second" >&2
  exit 1
fi
