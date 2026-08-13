#!/usr/bin/env bash
#
# ContentGrün dev-stack control script (agent sandbox VM).
#
# Everything runs in Docker via docker-compose.dev.yml. No subcommand leaves a
# process in the foreground, every subcommand terminates, and the exit code is
# the answer -- so an agent can branch on it without scraping output.
#
# Works from any directory: all paths are derived from this script's location.
#
# Subcommands:
#   up      build + start, wait until every container is healthy
#   status  one line per service (name port state) + Qdrant point count
#   reset   down (volumes kept) + start          <- default after code changes
#   wipe    down -v + start + seed               <- only for schema/seed problems
#   seed    trigger seeding, wait for completion
#   test    pytest (semantic search) + dotnet test (BFF)
#   logs    docker compose logs --tail 100 [service]
#   down    stop and remove containers (volumes kept)
#
# Why `reset` is the default: `wipe` throws away the Qdrant volume, so seeding
# has to run again -- that alone costs ~68s (measured: 30 files / 109 items /
# 181 points), on top of container startup. A code change never invalidates the
# vectors, so `reset` is the right loop. Reach for `wipe` only when the data
# itself is wrong: changed seed files, changed collection schema, or a Qdrant
# collection that got into a bad state.
#
# Exit codes:
#   0  success
#   1  runtime failure (container not healthy, seeding failed, tests failed;
#      for `status` also: content_collection is empty)
#   2  usage error / environment not usable (no Docker, compose file missing)

set -uo pipefail

# --- locate the repo (independent of the caller's cwd, symlink-safe) ----------
_src="${BASH_SOURCE[0]}"
while [ -L "$_src" ]; do
    _dir="$(cd -P "$(dirname "$_src")" && pwd)"
    _src="$(readlink "$_src")"
    [[ "$_src" != /* ]] && _src="$_dir/$_src"
done
SCRIPT_DIR="$(cd -P "$(dirname "$_src")" && pwd)"
MVP_DIR="$(cd -P "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$MVP_DIR/docker-compose.dev.yml"

SEMANTIC_URL="http://localhost:8000"
QDRANT_URL="http://localhost:6333"
COLLECTION="content_collection"

# Service name / container name / published host port, index-aligned.
SERVICES=(qdrant postgres-app contentgruen-semantic-search contentgruen-bff contentgruen-frontend)
CONTAINERS=(contentgruen-qdrant contentgruen-app-postgres contentgruen-semantic-search contentgruen-bff contentgruen-frontend)
HOST_PORTS=(6333 5433 8000 5054 8080)

HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-600}"   # seconds to wait for all containers
SEED_TIMEOUT="${SEED_TIMEOUT:-900}"       # seconds to wait for seeding

# --- output ------------------------------------------------------------------
# Colors only on a TTY; narration goes to stderr so `status` stdout stays clean.
if [ -t 2 ]; then
    C_RED=$'\033[0;31m'; C_GRN=$'\033[0;32m'; C_YEL=$'\033[1;33m'; C_OFF=$'\033[0m'
else
    C_RED=''; C_GRN=''; C_YEL=''; C_OFF=''
fi
info() { printf '%s\n' "$*" >&2; }
ok()   { printf '%s%s%s\n' "$C_GRN" "$*" "$C_OFF" >&2; }
warn() { printf '%swarning: %s%s\n' "$C_YEL" "$*" "$C_OFF" >&2; }
err()  { printf '%serror: %s%s\n' "$C_RED" "$*" "$C_OFF" >&2; }

dc() { docker compose -f "$COMPOSE_FILE" "$@"; }

preflight() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        err "compose file not found: $COMPOSE_FILE"
        exit 2
    fi
    if ! command -v docker >/dev/null 2>&1; then
        err "docker not found in PATH"
        exit 2
    fi
    if ! docker info >/dev/null 2>&1; then
        err "cannot talk to the Docker daemon"
        exit 2
    fi
}

# --- state helpers -----------------------------------------------------------
# healthy | starting | unhealthy | running (no healthcheck) | created | exited | down
container_state() {
    docker inspect -f \
        '{{if .State.Health}}{{.State.Health.Status}}{{else if eq .State.Status "running"}}running{{else}}{{.State.Status}}{{end}}' \
        "$1" 2>/dev/null || echo down
}

# Point count of the Qdrant collection, or "?" if Qdrant is not answering,
# or "absent" if the collection does not exist yet.
collection_points() {
    local body
    body="$(curl -fsS --max-time 5 "$QDRANT_URL/collections/$COLLECTION" 2>/dev/null)" || {
        curl -fsS --max-time 5 "$QDRANT_URL/collections" >/dev/null 2>&1 \
            && { echo absent; return; }
        echo '?'; return
    }
    local n
    n="$(printf '%s' "$body" | grep -o '"points_count":[0-9]*' | head -1 | cut -d: -f2)"
    [ -n "$n" ] && echo "$n" || echo 0
}

# Prints the status block. Return: 0 all healthy, 1 otherwise.
status_print() {
    local i state rc=0
    for i in "${!SERVICES[@]}"; do
        state="$(container_state "${CONTAINERS[$i]}")"
        printf '%s %s %s\n' "${SERVICES[$i]}" "${HOST_PORTS[$i]}" "$state"
        [ "$state" = healthy ] || rc=1
    done
    printf '%s points=%s\n' "$COLLECTION" "$(collection_points)"
    return $rc
}

# Wait until every container reports healthy. Fails fast when a container is
# not even running -- `Created`/`Exited` never becomes healthy on its own, so
# waiting out the timeout would only hide the error.
wait_healthy() {
    local deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
    local i state pending stuck
    while :; do
        pending=0; stuck=''
        for i in "${!SERVICES[@]}"; do
            state="$(container_state "${CONTAINERS[$i]}")"
            case "$state" in
                healthy) ;;
                created|exited|dead|down|paused|removing|restarting)
                    stuck+="${SERVICES[$i]}=$state " ;;
                *) pending=$(( pending + 1 )) ;;
            esac
        done
        if [ -n "$stuck" ]; then
            err "container(s) not running: $stuck"
            return 1
        fi
        [ "$pending" -eq 0 ] && return 0
        if [ "$(date +%s)" -ge "$deadline" ]; then
            err "timeout after ${HEALTH_TIMEOUT}s waiting for healthy containers"
            return 1
        fi
        sleep 3
    done
}

# --- subcommands -------------------------------------------------------------
cmd_up() {
    info "building and starting (compose project: contentgruen-dev)"
    if ! dc up -d --build >&2; then
        err "compose up failed"
        status_print
        exit 1
    fi
    if ! wait_healthy; then
        status_print
        exit 1
    fi
    ok "all containers healthy"
    status_print
    # A green stack with an empty collection is not an error for `up` itself,
    # but it is useless for verification -- so say so loudly.
    [ "$(collection_points)" = 0 ] && warn "$COLLECTION is empty -- run '$0 seed'"
    exit 0
}

cmd_status() {
    if status_print; then
        local pts
        pts="$(collection_points)"
        if [ "$pts" = 0 ] || [ "$pts" = absent ]; then
            err "$COLLECTION has no points -- sandbox has no data"
            exit 1
        fi
        exit 0
    fi
    exit 1
}

cmd_reset() {
    info "reset: recreating containers, keeping volumes"
    dc down >&2 || { err "compose down failed"; exit 1; }
    if ! dc up -d --build >&2; then
        err "compose up failed"
        status_print
        exit 1
    fi
    if ! wait_healthy; then
        status_print
        exit 1
    fi
    ok "all containers healthy"
    status_print
    exit 0
}

cmd_wipe() {
    info "wipe: removing volumes, rebuilding, reseeding"
    dc down -v >&2 || { err "compose down -v failed"; exit 1; }
    if ! dc up -d --build >&2; then
        err "compose up failed"
        status_print
        exit 1
    fi
    if ! wait_healthy; then
        status_print
        exit 1
    fi
    ok "all containers healthy"
    seed_run || exit 1
    status_print
    exit 0
}

# Trigger seeding and block until it is done. Return 0 on success.
seed_run() {
    local state
    state="$(container_state contentgruen-semantic-search)"
    if [ "$state" != healthy ]; then
        err "semantic search service is '$state', not healthy -- cannot seed"
        return 1
    fi

    # One request only -- a second POST would either race or come back 409.
    local raw body code
    raw="$(curl -sS -w '\n%{http_code}' -X POST "$SEMANTIC_URL/api/v1/seeding/start" 2>/dev/null)"
    code="$(printf '%s' "$raw" | tail -n1)"
    body="$(printf '%s' "$raw" | sed '$d')"
    # 409 = already running: fine, just wait for it below.
    if [ "$code" != 200 ] && [ "$code" != 409 ]; then
        err "seeding start returned HTTP $code"
        return 1
    fi
    case "$(json_field "$body" status)" in
        skipped)
            info "seeding skipped (no seed files found)"
            return 0 ;;
    esac

    info "seeding started, waiting for completion (~68s on an empty collection)"
    local deadline=$(( $(date +%s) + SEED_TIMEOUT ))
    local st
    while :; do
        st="$(json_field "$(curl -fsS --max-time 10 "$SEMANTIC_URL/api/v1/seeding/status" 2>/dev/null)" status)"
        case "$st" in
            completed) ok "seeding completed"; return 0 ;;
            failed)    err "seeding failed -- see '$0 logs contentgruen-semantic-search'"; return 1 ;;
        esac
        if [ "$(date +%s)" -ge "$deadline" ]; then
            err "timeout after ${SEED_TIMEOUT}s waiting for seeding (last status: ${st:-unknown})"
            return 1
        fi
        sleep 3
    done
}

# Minimal string-field extractor -- avoids a jq/python dependency.
json_field() {
    printf '%s' "$1" | grep -o "\"$2\":\"[^\"]*\"" | head -1 | cut -d'"' -f4
}

cmd_seed() {
    seed_run || exit 1
    printf '%s points=%s\n' "$COLLECTION" "$(collection_points)"
    exit 0
}

cmd_test() {
    local rc=0
    info "pytest (semantic search)"
    ( cd "$MVP_DIR/backend/semantic-search-service/app" && pytest -q ) || rc=1
    info "dotnet test (BFF)"
    ( cd "$MVP_DIR/backend" && dotnet test --nologo ) || rc=1
    [ "$rc" -eq 0 ] && ok "tests passed" || err "tests failed"
    exit "$rc"
}

cmd_logs() {
    local args=(logs --tail 100)
    [ -t 1 ] || args+=(--no-color)
    dc "${args[@]}" "$@"
    exit $?
}

cmd_down() {
    dc down >&2 || { err "compose down failed"; exit 1; }
    ok "stack down (volumes kept)"
    exit 0
}

usage() {
    sed -n '3,33p' "$_src" | sed 's/^# \{0,1\}//'
    exit 2
}

# --- dispatch ----------------------------------------------------------------
case "${1:-}" in
    up)     preflight; cmd_up ;;
    status) preflight; cmd_status ;;
    reset)  preflight; cmd_reset ;;
    wipe)   preflight; cmd_wipe ;;
    seed)   preflight; cmd_seed ;;
    test)   cmd_test ;;
    logs)   preflight; shift; cmd_logs "$@" ;;
    down)   preflight; cmd_down ;;
    ''|-h|--help|help) usage ;;
    *)      err "unknown subcommand: $1"; usage ;;
esac
