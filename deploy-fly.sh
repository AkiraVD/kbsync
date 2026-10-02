#!/usr/bin/env bash
# Run once to create the daily job. Needs: fly auth login.
set -euo pipefail

APP="${FLY_APP:-kbsync}"

fly apps list | grep -qE "^${APP}\s" || fly apps create "$APP"

echo "Secrets must already be set:"
echo "  fly secrets set -a $APP ZENDESK_HOST=... GEMINI_API_KEY=... GEMINI_FILE_SEARCH_STORE=..."

image="$(fly deploy --build-only --push -a "$APP" | grep -oE 'registry\.fly\.io/[^[:space:]]+' | tail -1)"
echo "built $image"

fly machine run "$image" --app "$APP" --schedule daily --restart no
fly machine list --app "$APP"
