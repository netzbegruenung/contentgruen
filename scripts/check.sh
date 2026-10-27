#!/bin/bash
# Full check for a working tree: Python lint + format + unit tests, frontend tests, BFF tests.
# The same command for people, agents and CI. Run from the repository root.
# Frontend tests need a Chrome/Chromium: set CHROME_BIN, otherwise the Playwright Chromium is used if present.
# --integration: also run app/tests/integration against Qdrant (QDRANT_URL, default localhost:6333) and
# PostgreSQL (POSTGRES_TEST_DATABASE_URL or a throwaway container); aborts if either is missing.
set -e
INTEGRATION=
for arg in "$@"; do
  case "$arg" in
    --integration) INTEGRATION=1 ;;
    *) echo "Unknown option: $arg (usage: check.sh [--integration])" >&2; exit 2 ;;
  esac
done
ROOT=$(git rev-parse --show-toplevel); PY=$ROOT/mvp/backend/semantic-search-service; FE=$ROOT/mvp/frontend/gutgesagt-frontend
if [ -z "$CHROME_BIN" ]; then CHROME_BIN=$(ls -d "$HOME"/.cache/ms-playwright/chromium-*/chrome-linux*/chrome 2>/dev/null | tail -1); export CHROME_BIN; fi

echo "== Retired words"; python3 "$ROOT/scripts/retired_words.py" --base "${CHECK_BASE:-origin/main}"

echo "== Python"; cd "$PY"
./venv/bin/python -m ruff check app/
./venv/bin/python -m black --check -q app/
./venv/bin/python -m pytest app/tests/unit/ --ignore=app/tests/unit/services/test_seeding_implementation.py -q 2>&1 | tail -2; test "${PIPESTATUS[0]}" -eq 0
if [ -n "$INTEGRATION" ]; then
  echo "== Python integration"
  # Shown: skip/failure/error summary lines, the abort message of a missing stack (Exit: and
  # its "- " lines, without pytest's repeat ending in "!") and the final count. For a
  # traceback rerun the failing test with pytest directly.
  INTEGRATION_STACK_PFLICHT=1 ./venv/bin/python -m pytest app/tests/integration/ -q -rfEs 2>&1 \
    | grep -aE '^(SKIPPED|FAILED|ERROR|Exit: )|^- .*[^!]$|^=+ .*[0-9.]+s( \([0-9:]+\))? =+$' | tail -40
  test "${PIPESTATUS[0]}" -eq 0
fi

echo "== Frontend"; cd "$FE"
[ -f src/environments/environment.ts ] || cp src/environments/environment.ts.template src/environments/environment.ts
npx ng test --watch=false --browsers=ChromeHeadless 2>&1 | grep -aE 'Executed [0-9]+ of [0-9]+ .*(SUCCESS|FAILED)|ERROR' | tail -2; test "${PIPESTATUS[0]}" -eq 0

echo "== BFF"; cd "$ROOT/mvp/backend"
docker run --rm -e HOME=/tmp -e DOTNET_CLI_HOME=/tmp -e NUGET_PACKAGES=/tmp/nuget \
  -v "$PWD":/src -v "${NUGET_CACHE:-$HOME/.cache/gutgesagt-nuget}":/tmp/nuget -w /src \
  mcr.microsoft.com/dotnet/sdk:9.0 dotnet test GutGesagt.sln --nologo -v q 2>&1 | grep -E 'Passed!|Failed!|error' | tail -3
test "${PIPESTATUS[0]}" -eq 0
echo "CHECK OK"
