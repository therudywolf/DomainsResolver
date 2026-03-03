#!/usr/bin/env bash
# 1) If input.txt hash unchanged -> skip pipeline, exit 0.
# 2) Else run pipeline.py, save hash to .input_hash.
# 3) Run sync.sh to git add/commit/push when output or hash changed.

set -e
INPUT_FILE="${INPUT_FILE:-input.txt}"
HASH_FILE="${HASH_FILE:-.input_hash}"
OUTPUT_FILE="${OUTPUT_FILE:-output_optimized.txt}"
SCRIPT_DIR="${SCRIPT_DIR:-.}"

cd "$SCRIPT_DIR"

if [ ! -f "$INPUT_FILE" ]; then
  echo "[ERROR] $INPUT_FILE not found."
  exit 1
fi

# Use sha256sum (GNU/Linux) or shasum -a 256 (macOS)
if command -v sha256sum >/dev/null 2>&1; then
  current_hash="$(sha256sum "$INPUT_FILE" | cut -d' ' -f1)"
elif command -v shasum >/dev/null 2>&1; then
  current_hash="$(shasum -a 256 "$INPUT_FILE" | cut -d' ' -f1)"
else
  echo "[ERROR] No sha256sum or shasum found."
  exit 1
fi

if [ -f "$HASH_FILE" ] && [ "$(cat "$HASH_FILE")" = "$current_hash" ]; then
  echo "[SKIP] input unchanged, skipping pipeline."
  exit 0
fi

python3 pipeline.py || exit 1
echo "$current_hash" > "$HASH_FILE"

# Sync to git if output or hash changed
if [ -f "sync.sh" ]; then
  ./sync.sh
else
  if git status --porcelain "$OUTPUT_FILE" "$HASH_FILE" 2>/dev/null | grep -q .; then
    git add "$OUTPUT_FILE" "$HASH_FILE"
    git commit -m "Auto-update IPs"
    [ -n "${GIT_PUSH_TOKEN}" ] && orig="$(git remote get-url origin 2>/dev/null)" && [[ "$orig" == https://* ]] && git remote set-url origin "https://oauth2:${GIT_PUSH_TOKEN}@${orig#https://}"
    git push
    echo "[PUSH] Done."
  fi
fi
