#!/usr/bin/env bash
# Запускается внутри контейнера. Проверка DNS + push.
set -e
cd /data

echo "=============================================="
echo "  DMTCDRK — проверка"
echo "=============================================="

echo "[1/3] DNS резолв..."
python3 pipeline.py
echo ""

[ -f output_verify.txt ] && echo "[2/3] Результат: $(wc -l < output_verify.txt) записей" || echo "[2/3] output_verify.txt не создан"
echo ""

echo "[3/3] Git push..."
if [ -z "${GIT_PUSH_TOKEN}" ]; then
  echo "[SKIP] GIT_PUSH_TOKEN не задан"
  exit 0
fi

orig=""
branch="${GIT_BRANCH:-$(git branch --show-current 2>/dev/null || echo main)}"
if orig="$(git remote get-url origin 2>/dev/null)" && [ -n "$orig" ] && [[ "$orig" == https://* ]]; then
  git remote set-url origin "https://oauth2:${GIT_PUSH_TOKEN}@${orig#https://}"
fi
if git push --dry-run origin "$branch" 2>/dev/null; then
  echo "[OK] Push доступен"
else
  echo "[WARN] Push не прошёл"
  exit 1
fi
[ -n "$orig" ] && git remote set-url origin "$orig"

echo ""
echo "=============================================="
echo "  Всё работает"
echo "=============================================="
