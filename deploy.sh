#!/usr/bin/env bash
# DMTCDRK — развёртывание на сервере
# Использование: ./deploy.sh [путь_к_проекту]
#             ./deploy.sh --no-verify  — без проверки

set -e
PROJECT_DIR="${1:-$(cd "$(dirname "$0")" && pwd)}"
[ "$1" = "--no-verify" ] && PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)" && SKIP_VERIFY=1
[ "$1" != "--no-verify" ] && SKIP_VERIFY=""
cd "$PROJECT_DIR"

# Загрузка .env
[ -f .env ] && set -a && . ./.env && set +a

echo "[DEPLOY] DMTCDRK → $PROJECT_DIR"

# Проверки
if [ ! -f ".env" ]; then
  echo "[ERROR] .env не найден. Скопируй: cp .env.example .env"
  exit 1
fi

if ! grep -q "GIT_PUSH_TOKEN=ghp_" .env 2>/dev/null; then
  echo "[WARN] GIT_PUSH_TOKEN не заполнен в .env"
fi

# Сборка (нужна для verify)
echo "[DEPLOY] Сборка образа..."
docker compose build

# Первый запуск: проверка (через Docker)
if [ -z "$SKIP_VERIFY" ] && [ ! -f ".deploy_done" ]; then
  echo "[DEPLOY] Первый запуск — проверка DNS и push..."
  chmod +x verify.sh 2>/dev/null || true
  # Запуск verify: можно через ./verify.sh (нужен Python) или docker
  if docker compose run --rm \
    -e INPUT_FILE=verify_input.txt \
    -e OUTPUT_FILE=output_verify.txt \
    -e HASH_FILE=.verify_hash \
    -e LOG_LEVEL=DEBUG \
    -e FORCE_RUN=1 \
    -e USE_DOMAIN_CACHE=0 \
    app bash -c "python3 pipeline.py" 2>/dev/null; then
    echo "[OK] DNS резолв проверен"
    # Тест push (dry-run)
    if [ -n "${GIT_PUSH_TOKEN}" ]; then
      branch="${GIT_BRANCH:-$(git branch --show-current 2>/dev/null || echo main)}"
      orig="$(git remote get-url origin 2>/dev/null)" && [ -n "$orig" ] && [[ "$orig" == https://* ]] && \
        git remote set-url origin "https://oauth2:${GIT_PUSH_TOKEN}@${orig#https://}"
      if git push --dry-run origin "$branch" 2>/dev/null; then
        echo "[OK] Push доступен"
      fi
      [ -n "$orig" ] && git remote set-url origin "$orig"
    fi
    touch .deploy_done
    echo ""
  else
    echo "[WARN] Проверка не прошла. Запусти ./verify.sh вручную. Продолжить deploy? (y/n)"
    read -r ans
    [ "$ans" != "y" ] && [ "$ans" != "Y" ] && exit 1
  fi
fi

echo "[DEPLOY] Запуск daemon в фоне..."
docker compose up -d daemon

echo "[DEPLOY] Готово. Логи: docker compose logs -f daemon"
