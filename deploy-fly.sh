#!/usr/bin/env bash
# Create (or refresh) the daily job on Fly. Run after `fly auth login`.
set -euo pipefail

APP="${FLY_APP:-$(awk -F'"' '/^app =/ {print $2}' fly.toml)}"
KEYS='^(ZENDESK_HOST|GEMINI_API_KEY|GEMINI_FILE_SEARCH_STORE)=.+'

echo "app: $APP"

if ! fly status -a "$APP" >/dev/null 2>&1; then
  fly apps create "$APP"
fi

# Straight from .env, so the key never reaches the shell history or a process list.
grep -E "$KEYS" .env | fly secrets import -a "$APP"

build_args=(--build-only --push -a "$APP")
if docker info >/dev/null 2>&1; then
  build_args+=(--local-only)
fi

image="$(fly deploy "${build_args[@]}" | tee /dev/stderr \
  | grep -oE 'registry\.fly\.io/[^[:space:]]+' | tail -1)"

if [ -z "$image" ]; then
  echo "could not read the image reference from fly deploy output" >&2
  exit 1
fi
echo "image: $image"

fly machine run "$image" -a "$APP" --schedule daily --restart no
fly machine list -a "$APP"

echo
echo "Next run is on Fly's daily schedule. To run it now:"
echo "  fly machine list -a $APP        # copy the id"
echo "  fly machine start <id> -a $APP"
echo "  fly logs -a $APP"
