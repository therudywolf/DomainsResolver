#!/usr/bin/env bash
# DMTCDRK — развёртывание на сервере
# Использование: ./deploy.sh [путь_к_проекту]
#             ./deploy.sh --no-verify  — без проверки

set -e
PROJECT_DIR="${1:-$(cd "$(dirname "$0")" && pwd)}"
[ "$1" = "--no-verify" ] && PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)" && SKIP_VERIFY=1
[ "$1" != "--no-verify" ] && SKIP_VERIFY=""
cd "$PROJECT_DIR"

# Загрузка .env (убираем CRLF для Linux)
[ -f .env ] && set -a && . <(sed 's/\r$//' .env) && set +a

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
  if ./verify.sh; then
    touch .deploy_done
    echo ""
  else
    echo "[WARN] verify.sh не прошёл. Продолжить deploy? (y/n)"
    read -r ans
    [ "$ans" != "y" ] && [ "$ans" != "Y" ] && exit 1
  fi
fi

echo "[DEPLOY] Запуск daemon в фоне..."
docker compose up -d daemon

echo "[DEPLOY] Готово. Логи: docker compose logs -f daemon"
