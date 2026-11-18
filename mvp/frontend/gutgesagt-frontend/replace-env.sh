#!/bin/sh
# Replace placeholder values in Angular's built files with environment variables.
# HTML_DIR only for tests (scripts/tests/test_replace_env.py).
HTML_DIR="${HTML_DIR:-/usr/share/nginx/html}"

for file in "$HTML_DIR"/*.js; do
  sed -i "s|\${PRODUCTION}|${PRODUCTION}|g" "$file"
  sed -i "s|\${API_BASE_URL}|${API_BASE_URL}|g" "$file"
  sed -i "s|\${USE_KEYCLOAK}|${USE_KEYCLOAK}|g" "$file"
done

# Commit and version for the footer go into index.html, which nginx serves without cache.
# The *.js names are hashed before this script runs and are cached for a year, so a value
# substituted there stayed stale in browsers that had the file from an older build.
sed -i "s|\${GIT_SHA}|${GIT_SHA:-dev}|g" "$HTML_DIR/index.html"
sed -i "s|\${APP_VERSION}|${APP_VERSION}|g" "$HTML_DIR/index.html"
