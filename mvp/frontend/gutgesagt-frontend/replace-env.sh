#!/bin/sh
# Replace placeholder values in Angular's built files with environment variables.
# HTML_DIR only for tests (scripts/tests/test_replace_env.py).
set -eu
HTML_DIR="${HTML_DIR:-/usr/share/nginx/html}"

if [ ! -f "$HTML_DIR/index.html" ]; then
  echo "replace-env.sh: $HTML_DIR/index.html missing, nothing to substitute" >&2
  exit 1
fi

for file in "$HTML_DIR"/*.js; do
  [ -f "$file" ] || continue
  sed -i "s|\${PRODUCTION}|${PRODUCTION-}|g" "$file"
  sed -i "s|\${API_BASE_URL}|${API_BASE_URL-}|g" "$file"
  sed -i "s|\${USE_KEYCLOAK}|${USE_KEYCLOAK-}|g" "$file"
done

# Commit and version go into an HTML attribute and a sed replacement: only characters that
# are harmless in both (no "|", "&", quotes or "<"). Anything else falls back like a build
# without the argument, so an odd tag name cannot break the page.
nur_kennungszeichen() {
  case "$1" in
    *[!0-9A-Za-z._+-]*) return 1 ;;
    *) return 0 ;;
  esac
}

GIT_SHA="${GIT_SHA:-dev}"
if ! nur_kennungszeichen "$GIT_SHA"; then
  echo "replace-env.sh: GIT_SHA has characters outside [0-9A-Za-z._+-], using dev" >&2
  GIT_SHA=dev
fi
APP_VERSION="${APP_VERSION-}"
if ! nur_kennungszeichen "$APP_VERSION"; then
  echo "replace-env.sh: APP_VERSION has characters outside [0-9A-Za-z._+-], leaving it empty" >&2
  APP_VERSION=
fi

# Commit and version for the footer go into index.html, which nginx serves without cache.
# The *.js names are hashed before this script runs and are cached for a year, so a value
# substituted there stayed stale in browsers that had the file from an older build.
sed -i "s|\${GIT_SHA}|${GIT_SHA}|g" "$HTML_DIR/index.html"
sed -i "s|\${APP_VERSION}|${APP_VERSION}|g" "$HTML_DIR/index.html"
