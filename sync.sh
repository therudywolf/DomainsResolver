#!/usr/bin/env bash
# If output_optimized.txt changed, git add, commit, push.
# .input_hash не коммитим (он в .gitignore) — только выходной файл.
# Uses GIT_PUSH_TOKEN for HTTPS push when set. Restores origin URL after push.
# Retries git push up to 3 times on failure.

set -e
OUTPUT_FILE="${OUTPUT_FILE:-output_optimized.txt}"
GIT_PUSH_RETRIES="${GIT_PUSH_RETRIES:-3}"
GIT_PUSH_SLEEP="${GIT_PUSH_SLEEP:-5}"

# Git config (нужно для commit в контейнере)
git config user.name "${GIT_USER_NAME:-DMTCDRK}" 2>/dev/null || true
git config user.email "${GIT_USER_EMAIL:-dmtcdrk@localhost}" 2>/dev/null || true

# Проверяем только выходной файл — хеш в репозиторий не пушим
if ! git status --porcelain "$OUTPUT_FILE" 2>/dev/null | grep -q .; then
  echo "[SYNC] Нет изменений в $OUTPUT_FILE — push не нужен"
  exit 0
fi

echo "[SYNC] Изменения обнаружены, коммит и push..."
git add "$OUTPUT_FILE"
# Если после add ничего не изменилось относительно HEAD (файл перезаписан тем же) — не коммитим
if git diff --cached --quiet 2>/dev/null; then
  echo "[SYNC] Нет изменений в $OUTPUT_FILE относительно HEAD — push не нужен"
  exit 0
fi
if [ -n "${GIT_SIGN_COMMITS}" ] && [ "${GIT_SIGN_COMMITS}" != "0" ] && [ "${GIT_SIGN_COMMITS}" != "false" ] && [ "${GIT_SIGN_COMMITS}" != "no" ]; then
  git commit -S -m "Auto-update IPs"
else
  git commit -m "Auto-update IPs"
fi

orig=""
if [ -n "${GIT_PUSH_TOKEN}" ]; then
  orig="$(git remote get-url origin 2>/dev/null || true)"
  if [ -n "$orig" ] && [[ "$orig" == https://* ]]; then
    new="${orig#https://}"
    git remote set-url origin "https://oauth2:${GIT_PUSH_TOKEN}@${new}"
  fi
fi

attempt=1
branch="${GIT_BRANCH:-$(git branch --show-current)}"
while true; do
  if git push origin "$branch"; then
    break
  fi
  if [ "$attempt" -ge "$GIT_PUSH_RETRIES" ]; then
    echo "[ERROR] git push failed after $GIT_PUSH_RETRIES attempts." >&2
    [ -n "$orig" ] && git remote set-url origin "$orig"
    exit 1
  fi
  echo "[WARN] git push failed (attempt $attempt), retrying in ${GIT_PUSH_SLEEP}s..."
  sleep "$GIT_PUSH_SLEEP"
  attempt=$((attempt + 1))
done

[ -n "$orig" ] && git remote set-url origin "$orig"
echo "[PUSH] Готово. Ветка $branch"
