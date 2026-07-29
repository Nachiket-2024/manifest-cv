#!/usr/bin/env bash
# Starts the full stack and waits for every long-running service to
# actually report healthy (or just running, for the one service with no
# healthcheck) before showing anything else : so a real startup failure is
# a clean one-line-per-service table, not a scroll of interleaved logs to
# spot it in.
#
# Deliberately does NOT use `docker compose up --wait`: this repo's compose
# file includes one-shot init containers (alembic, bugsink-seed) that are
# *supposed* to exit 0 once their job is done, but `--wait` treats any
# exited container as a failure to reach "running", regardless of exit
# code : it would report this stack as failed on every single successful
# start. This polls the actual long-running services directly instead.
#
# On success, tails only backend + frontend + taskiq_worker: real request
# traffic, the frontend dev server's own activity, and async email-task
# execution. It still excludes Postgres/Redis/Bugsink/Alembic internals and
# Bugsink's own health-check polling noise. Backend exceptions still go to
# Bugsink (http://localhost:8010), that's what it's for, not this terminal.
# backend and taskiq_worker are also explicitly `restart`ed after `up -d` so
# their boot banner (Uvicorn's startup lines, Taskiq's "Listening started")
# is always visible in that tail, even when this script is rerun against a
# stack that was already up and neither container needed recreating.
#
# This is the recommended day-to-day command : see README.md. Use plain
# `docker compose up` instead when you actually want every service's full
# logs in one stream (e.g. debugging Postgres/Bugsink/Taskiq startup itself).
#
# Usage: ./scripts/dev-up.sh   (Git Bash or WSL on Windows)
# PowerShell: .\scripts\dev-up.ps1
# Command Prompt: scripts\dev-up.cmd
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# frontend has no healthcheck defined (docker-compose.yml) : "Up" is as
# ready as it gets. Every other long-running service does have one.
LONG_RUNNING_SERVICES=(postgres redis bugsink backend taskiq_worker frontend)
TIMEOUT_SECONDS=180
POLL_INTERVAL=2
TAIL_SINCE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

is_ready() {
    local status
    status="$(docker compose ps --format '{{.Status}}' "$1" 2>/dev/null)"
    case "$status" in
        *"(healthy)"*) return 0 ;;
        "Up "*) [ "$1" = "frontend" ] && return 0 || return 1 ;;
        *) return 1 ;;
    esac
}

is_failed() {
    local status
    status="$(docker compose ps --format '{{.Status}}' "$1" 2>/dev/null)"
    case "$status" in
        *"Exited"*|*"Restarting"*|"") return 0 ;;
        *) return 1 ;;
    esac
}

docker compose up -d

# backend/taskiq_worker are the two services whose boot banner (Uvicorn's
# "Application startup complete", Taskiq's "Listening started", etc.) is
# actually useful to see. `docker compose up -d` leaves an already-running
# container alone when nothing about it changed, so on a rerun against a
# live stack those banners are from whenever it originally booted : older
# than $TAIL_SINCE below, so the tail at the bottom would silently skip
# them. Restarting the two here guarantees a fresh banner inside the
# --since window on every run, not just the first.
docker compose restart backend taskiq_worker

echo
printf "Waiting for services to come up"
elapsed=0
failed_service=""
not_ready=1
while [ "$elapsed" -lt "$TIMEOUT_SECONDS" ]; do
    not_ready=0
    for svc in "${LONG_RUNNING_SERVICES[@]}"; do
        if is_failed "$svc"; then
            failed_service="$svc"
            break
        fi
        is_ready "$svc" || not_ready=$((not_ready + 1))
    done
    [ -n "$failed_service" ] && break
    [ "$not_ready" -eq 0 ] && break
    printf "."
    sleep "$POLL_INTERVAL"
    elapsed=$((elapsed + POLL_INTERVAL))
done
echo
echo

echo "--- Stack status ---"
docker compose ps --format "table {{.Service}}\t{{.Status}}"
echo

if [ -n "$failed_service" ]; then
    echo "--- '$failed_service' failed to start ---"
    echo "Check its logs: docker compose logs $failed_service"
    exit 1
elif [ "$not_ready" -ne 0 ]; then
    echo "--- Timed out after ${TIMEOUT_SECONDS}s waiting for services to become healthy ---"
    echo "Check whichever service above isn't healthy: docker compose logs <service>"
    exit 1
fi

echo "--- Tailing backend + frontend + taskiq_worker (Ctrl+C stops watching, stack keeps running) ---"
echo "Backend errors/exceptions: http://localhost:8010 (Bugsink)"
echo
exec docker compose logs --since "$TAIL_SINCE" -f backend frontend taskiq_worker
