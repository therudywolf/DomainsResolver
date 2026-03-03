#!/usr/bin/env bash
# Проверка DNS + push. Запускается в контейнере.
set -e
cd /data

echo "=============================================="
echo "  DMTCDRK — проверка"
echo "=============================================="
echo "DELAY=${DELAY:-1.0}s  CONCURRENCY=${CONCURRENCY_LIMIT:-1}"
echo ""

# Git config (нужно для commit)
git config user.name "${GIT_USER_NAME:-DMTCDRK}" 2>/dev/null || true
git config user.email "${GIT_USER_EMAIL:-dmtcdrk@localhost}" 2>/dev/null || true

echo "[1/4] DNS резолв (медленно, без бана)..."
python3 pipeline.py
echo ""

if [ ! -f output_verify.txt ]; then
  echo "[ERROR] output_verify.txt не создан"
  exit 1
fi
echo "[2/4] Результат: $(wc -l < output_verify.txt) записей"
echo ""

echo "[3/4] Проверка git push..."
if [ -z "${GIT_PUSH_TOKEN}" ]; then
  echo "[SKIP] GIT_PUSH_TOKEN не задан — push не проверяется"
  echo ""
  echo "=============================================="
  echo "  DNS OK. Добавь GIT_PUSH_TOKEN в .env"
  echo "=============================================="
  exit 0
fi

orig=""
branch="${GIT_BRANCH:-$(git branch --show-current 2>/dev/null || echo main)}"
if ! orig="$(git remote get-url origin 2>/dev/null)" || [ -z "$orig" ]; then
  echo "[WARN] git remote origin не настроен"
  exit 1
fi
if [[ "$orig" != https://* ]]; then
  echo "[WARN] origin должен быть https://..."
  exit 1
fi

git remote set-url origin "https://oauth2:${GIT_PUSH_TOKEN}@${orig#https://}"

# Dry-run
if ! git push --dry-run origin "$branch" 2>&1; then
  echo "[ERROR] git push --dry-run не прошёл. Проверь GIT_PUSH_TOKEN"
  git remote set-url origin "$orig"
  exit 1
fi
git remote set-url origin "$orig"
echo "[OK] Push доступен (dry-run)"
echo ""

# Реальный push (опционально, для полной проверки)
if [ "${VERIFY_REAL_PUSH}" = "1" ] || [ "${VERIFY_REAL_PUSH}" = "true" ]; then
  echo "[4/4] Тест реального push..."
  if git status --porcelain output_verify.txt .verify_hash 2>/dev/null | grep -q .; then
    OUTPUT_FILE=output_verify.txt HASH_FILE=.verify_hash bash sync.sh
    echo "[OK] Push выполнен"
  else
    echo "[OK] Изменений нет"
  fi
else
  echo "[4/4] Dry-run пройден (для реального push: VERIFY_REAL_PUSH=1)"
fi

echo ""
echo "=============================================="
echo "  Всё работает. Запускай: ./start.sh"
echo "=============================================="
