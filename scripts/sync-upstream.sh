#!/usr/bin/env bash
# On-demand: pulls in updates from the original mystic-auth template repo.
# Nothing here runs automatically — this only does anything when you run it.
# See docs/mystic_auth/template-usage.md#staying-in-sync-with-upstream-template-updates
# for the full explanation of what conflicts and what almost never will.
#
# Usage: scripts/sync-upstream.sh [upstream-url]
#   upstream-url defaults to the original template repo; pass your own fork's
#   URL if you're syncing from somewhere else.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

UPSTREAM_URL="${1:-https://github.com/Nachiket-2024/mystic-auth.git}"

if git remote get-url upstream >/dev/null 2>&1; then
  echo "Using existing 'upstream' remote: $(git remote get-url upstream)"
else
  echo "Adding 'upstream' remote: $UPSTREAM_URL"
  git remote add upstream "$UPSTREAM_URL"
fi

echo "Fetching upstream..."
git fetch upstream

UPSTREAM_BRANCH="$(git remote show upstream | sed -n '/HEAD branch/s/.*: //p')"
UPSTREAM_BRANCH="${UPSTREAM_BRANCH:-main}"

INCOMING="$(git log "HEAD..upstream/${UPSTREAM_BRANCH}" --oneline)"

if [ -z "$INCOMING" ]; then
  echo "Already up to date with upstream/${UPSTREAM_BRANCH}."
  exit 0
fi

echo ""
echo "Incoming commits from upstream/${UPSTREAM_BRANCH}:"
echo "$INCOMING"
echo ""

read -r -p "Merge these into the current branch now? [y/N] " CONFIRM
case "$CONFIRM" in
  [yY]|[yY][eE][sS]) ;;
  *) echo "Not merging. Run this script again whenever you're ready."; exit 0 ;;
esac

if ! git merge "upstream/${UPSTREAM_BRANCH}" 2>/tmp/sync-upstream-merge.log; then
  if grep -q "refusing to merge unrelated histories" /tmp/sync-upstream-merge.log; then
    echo "First sync since this repo was created via 'Use this template' — no shared git history yet."
    echo "Retrying with --allow-unrelated-histories (only needed this once)..."
    git merge "upstream/${UPSTREAM_BRANCH}" --allow-unrelated-histories
  else
    cat /tmp/sync-upstream-merge.log
    exit 1
  fi
fi
rm -f /tmp/sync-upstream-merge.log

cat <<'EOF'

Merged. Before trusting this, rebuild and rerun the test suite — a merge
can change behavior underneath you even when every conflict resolved
automatically:

  docker compose up -d --build
  docker compose exec -w /repo backend python -m pytest tests/backend/mystic_auth/unit tests/backend/mystic_auth/integration tests/backend/mystic_auth/security
  # frontend: see docs/mystic_auth/testing/overview.md for the equivalent commands
EOF
