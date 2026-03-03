#!/usr/bin/env bash
# Первый запуск: проверка DNS-резолва и git push.
# ./verify.sh — тест без пуша в репо
# ./verify.sh --push — полный тест с реальным push

set -e
SCRIPT_DIR="${SCRIPT_DIR:-.}"
cd "$SCRIPT_DIR"

VERIFY_INPUT="${VERIFY_INPUT:-verify_input.txt}"
VERIFY_OUTPUT="${VERIFY_OUTPUT:-output_verify.txt}"
VERIFY_HASH="${VERIFY_HASH:-.verify_hash}"
DO_PUSH=""
[ "${1}" = "--push" ] && DO_PUSH=1

echo "=============================================="
echo "  DMTCDRK — проверка первого запуска"
echo "=============================================="
echo ""

# 1. Проверка verify_input.txt
if [ ! -f "$VERIFY_INPUT" ]; then
  echo "[ERROR] $VERIFY_INPUT не найден."
  exit 1
fi
echo "[1/4] Входной файл: $VERIFY_INPUT ($(wc -l < "$VERIFY_INPUT" | tr -d ' ') строк)"
echo ""

# 2. Загрузка .env
if [ -f ".env" ]; then
  set -a
  . ./.env
  set +a
  echo "[2/4] .env загружен"
else
  echo "[WARN] .env не найден, используются дефолты"
fi
echo ""

# 3. DNS + пайплайн (с отладкой)
echo "[3/4] Запуск пайплайна (LOG_LEVEL=DEBUG)..."
echo "----------------------------------------------"
INPUT_FILE="$VERIFY_INPUT" OUTPUT_FILE="$VERIFY_OUTPUT" HASH_FILE="$VERIFY_HASH" \
  LOG_LEVEL=DEBUG FORCE_RUN=1 USE_DOMAIN_CACHE=0 \
  python3 pipeline.py
echo "----------------------------------------------"
echo ""

if [ ! -f "$VERIFY_OUTPUT" ]; then
  echo "[ERROR] Пайплайн не создал $VERIFY_OUTPUT"
  exit 1
fi
ENTRIES=$(wc -l < "$VERIFY_OUTPUT" | tr -d ' ')
echo "[OK] Резолв и оптимизация: $VERIFY_OUTPUT ($ENTRIES записей)"
echo ""

# 4. Проверка git push
echo "[4/4] Проверка git push..."
if [ -z "${GIT_PUSH_TOKEN}" ]; then
  echo "[SKIP] GIT_PUSH_TOKEN не задан — push не проверяется"
  echo ""
  echo "=============================================="
  echo "  Итог: DNS OK. Добавь GIT_PUSH_TOKEN в .env"
  echo "=============================================="
  exit 0
fi

if [ -n "$DO_PUSH" ]; then
  # Реальный push verify-результата (output_verify.txt)
  if git status --porcelain "$VERIFY_OUTPUT" "$VERIFY_HASH" 2>/dev/null | grep -q .; then
    OUTPUT_FILE="$VERIFY_OUTPUT" HASH_FILE="$VERIFY_HASH" ./sync.sh
    echo "[OK] Push выполнен (verify)"
  else
    # Нет изменений — dry-run для проверки доступа
    orig=""
    branch="${GIT_BRANCH:-$(git branch --show-current 2>/dev/null || echo main)}"
    if orig="$(git remote get-url origin 2>/dev/null)" && [ -n "$orig" ] && [[ "$orig" == https://* ]]; then
      git remote set-url origin "https://oauth2:${GIT_PUSH_TOKEN}@${orig#https://}"
    fi
    git push --dry-run origin "$branch" 2>/dev/null && echo "[OK] Push доступен"
    [ -n "$orig" ] && git remote set-url origin "$orig"
  fi
else
  # Dry-run: проверка доступа без пуша
  orig=""
  branch="${GIT_BRANCH:-$(git branch --show-current 2>/dev/null || echo main)}"
  if orig="$(git remote get-url origin 2>/dev/null)" && [ -n "$orig" ] && [[ "$orig" == https://* ]]; then
    git remote set-url origin "https://oauth2:${GIT_PUSH_TOKEN}@${orig#https://}"
  fi
  if git push --dry-run origin "$branch" 2>/dev/null; then
    echo "[OK] Push доступен (dry-run)"
  else
    echo "[WARN] git push --dry-run не прошёл. Проверь GIT_PUSH_TOKEN и remote."
  fi
  [ -n "$orig" ] && git remote set-url origin "$orig"
fi

echo ""
echo "=============================================="
echo "  Всё работает. Запускай: ./run.sh или deploy.sh"
echo "=============================================="
