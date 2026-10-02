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
# Skipped when they are already set: `fly secrets import` reads app config from
# existing Machines, so it fails on an app whose Machine has been destroyed.
if fly secrets list -a "$APP" 2>/dev/null | grep -q GEMINI_API_KEY; then
  echo "secrets already set"
else
  grep -E "$KEYS" .env | fly secrets import -a "$APP"
fi

build_args=(--build-only --push -a "$APP")
if docker info >/dev/null 2>&1; then
  build_args+=(--local-only)
fi

# flyctl prints progress, and the image reference, on stderr.
image="$(fly deploy "${build_args[@]}" 2>&1 | tee /dev/stderr \
  | sed -n 's/^image: //p' | tail -1)"

if [ -z "$image" ]; then
  echo "could not read the image reference from fly deploy output" >&2
  exit 1
fi
echo "image: $image"

fly machine run "$image" -a "$APP" --schedule daily --restart no
fly machine list -a "$APP"

echo
echo "The Machine ran once on creation and now waits for its daily schedule."
echo "  fly logs -a $APP                 # that run's output"
echo "  fly machine start <id> -a $APP   # run it again on demand"
echo "  fly apps destroy $APP            # when it is no longer needed"
