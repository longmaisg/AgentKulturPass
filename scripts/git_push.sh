#!/bin/bash
# Usage: ./scripts/git_push.sh "message"
set -e
MSG="${1:-update}"
DATE=$(date '+%Y-%m-%d %H:%M')
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  echo "Nothing to commit."
  exit 0
fi
git add -A
git status --short
git commit -m "[$DATE] $MSG"
git push origin main
echo "✓ Pushed: $MSG"
