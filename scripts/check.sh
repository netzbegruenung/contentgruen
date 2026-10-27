#!/bin/bash
# Full check for a working tree: Python lint + format + unit tests, frontend tests, BFF tests.
# The same command for people, agents and CI. Run from the repository root.
# Frontend tests need a Chrome/Chromium: set CHROME_BIN, otherwise the Playwright Chromium is used if present.
# --integration: also run app/tests/integration against Qdrant (QDRANT_URL, default localhost:6333) and
# PostgreSQL (POSTGRES_TEST_DATABASE_URL or a throwaway container); aborts if either is missing.
# --schritt <name>: run only that step (retired-words, lint, unit, integration, frontend, bff);
# the Woodpecker pipeline (.woodpecker/ci.yaml) runs each step this way, see docs/CI.md.
# CHECK_VOLL=1 shows the full output instead of the summary lines; CHECK_OHNE_DOCKER=1 runs the
# BFF tests with the local dotnet instead of the .NET SDK container.
set -e
INTEGRATION=
SCHRITT=
SCHRITTE="retired-words lint unit integration frontend bff"
while [ $# -gt 0 ]; do
  case "$1" in
    --integration) INTEGRATION=1 ;;
    --schritt)
      SCHRITT=$2; shift
      case " $SCHRITTE " in *" $SCHRITT "*) ;; *) echo "Unknown step: $SCHRITT (one of: $SCHRITTE)" >&2; exit 2 ;; esac ;;
    *) echo "Unknown option: $1 (usage: check.sh [--integration] [--schritt <name>])" >&2; exit 2 ;;
  esac
  shift
done
# Whether step $1 runs: all steps without --schritt (integration only with --integration), else the one asked for
laeuft() { if [ -n "$SCHRITT" ]; then [ "$SCHRITT" = "$1" ]; else [ "$1" != integration ] || [ -n "$INTEGRATION" ]; fi; }
# Summary lines of a test run (grep pattern $1, last $2 lines), or everything with CHECK_VOLL=1
kurz() { if [ -n "$CHECK_VOLL" ]; then cat; else grep -aE "$1" | tail -n "$2"; fi; }
# Not git rev-parse: the CI images for Python and the BFF have no git
ROOT=$(cd "$(dirname "$0")/.." && pwd); PY=$ROOT/mvp/backend/semantic-search-service; FE=$ROOT/mvp/frontend/gutgesagt-frontend
if [ -z "$CHROME_BIN" ]; then CHROME_BIN=$(ls -d "$HOME"/.cache/ms-playwright/chromium-*/chrome-linux*/chrome 2>/dev/null | tail -1); export CHROME_BIN; fi

if laeuft retired-words; then
  echo "== Retired words"; python3 "$ROOT/scripts/retired_words.py" --base "${CHECK_BASE:-origin/main}"
fi

cd "$PY"
if laeuft lint; then
  echo "== Python lint"
  ./venv/bin/python -m ruff check app/
  ./venv/bin/python -m black --check -q app/
fi
if laeuft unit; then
  echo "== Python unit"
  ./venv/bin/python -m pytest app/tests/unit/ --ignore=app/tests/unit/services/test_seeding_implementation.py -q 2>&1 | kurz . 2; test "${PIPESTATUS[0]}" -eq 0
  ./venv/bin/python -m pytest "$ROOT/scripts/tests/" -q 2>&1 | kurz . 2; test "${PIPESTATUS[0]}" -eq 0
fi
if laeuft integration; then
  echo "== Python integration"
  # Shown: skip/failure/error summary lines, the abort message of a missing stack (Exit: and
  # its "- " lines, without pytest's repeat ending in "!") and the final count. For a
  # traceback rerun the failing test with pytest directly.
  INTEGRATION_STACK_PFLICHT=1 ./venv/bin/python -m pytest app/tests/integration/ -q -rfEs 2>&1 \
    | kurz '^(SKIPPED|FAILED|ERROR|Exit: )|^- .*[^!]$|^=+ .*[0-9.]+s( \([0-9:]+\))? =+$' 40
  test "${PIPESTATUS[0]}" -eq 0
fi

if laeuft frontend; then
  echo "== Frontend"; cd "$FE"
  [ -f src/environments/environment.ts ] || cp src/environments/environment.ts.template src/environments/environment.ts
  npx ng test --watch=false --browsers=ChromeHeadless --progress=false 2>&1 | kurz 'Executed [0-9]+ of [0-9]+ .*(SUCCESS|FAILED)|ERROR' 2; test "${PIPESTATUS[0]}" -eq 0
fi

if laeuft bff; then
  echo "== BFF"; cd "$ROOT/mvp/backend"
  if [ -n "$CHECK_OHNE_DOCKER" ]; then
    dotnet test GutGesagt.sln --nologo -v q 2>&1 | kurz 'Passed!|Failed!|error' 3
  else
    docker run --rm -e HOME=/tmp -e DOTNET_CLI_HOME=/tmp -e NUGET_PACKAGES=/tmp/nuget \
      -v "$PWD":/src -v "${NUGET_CACHE:-$HOME/.cache/gutgesagt-nuget}":/tmp/nuget -w /src \
      mcr.microsoft.com/dotnet/sdk:9.0 dotnet test GutGesagt.sln --nologo -v q 2>&1 | kurz 'Passed!|Failed!|error' 3
  fi
  test "${PIPESTATUS[0]}" -eq 0
fi
echo "CHECK OK"
