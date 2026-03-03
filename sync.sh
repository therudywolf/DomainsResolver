#!/usr/bin/env bash
# If output_optimized.txt or .input_hash changed, git add, commit, push.
# Uses GIT_PUSH_TOKEN for HTTPS push when set.

set -e
OUTPUT_FILE="${OUTPUT_FILE:-output_optimized.txt}"
HASH_FILE="${HASH_FILE:-.input_hash}"

if ! git status --porcelain "$OUTPUT_FILE" "$HASH_FILE" 2>/dev/null | grep -q .; then
  echo "[SKIP] No changes to $OUTPUT_FILE or $HASH_FILE, nothing to push."
  exit 0
fi

git add "$OUTPUT_FILE" "$HASH_FILE"
git commit -m "Auto-update IPs"

if [ -n "${GIT_PUSH_TOKEN}" ]; then
  orig="$(git remote get-url origin 2>/dev/null || true)"
  if [ -n "$orig" ] && [[ "$orig" == https://* ]]; then
    new="${orig#https://}"
    git remote set-url origin "https://oauth2:${GIT_PUSH_TOKEN}@${new}"
  fi
fi

git push
echo "[PUSH] Done."
