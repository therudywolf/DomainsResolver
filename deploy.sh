#!/usr/bin/env bash
# DMTCDRK — развёртывание на сервере
# Использование: ./deploy.sh [путь_к_проекту]

set -e
PROJECT_DIR="${1:-$(cd "$(dirname "$0")" && pwd)}"
cd "$PROJECT_DIR"

echo "[DEPLOY] DMTCDRK → $PROJECT_DIR"

# Проверки
if [ ! -f ".env" ]; then
  echo "[ERROR] .env не найден. Скопируй: cp .env.example .env"
  exit 1
fi

if ! grep -q "GIT_PUSH_TOKEN=ghp_" .env 2>/dev/null; then
  echo "[WARN] GIT_PUSH_TOKEN не заполнен в .env"
fi

# Сборка и запуск daemon
echo "[DEPLOY] Сборка образа..."
docker compose build

echo "[DEPLOY] Запуск daemon в фоне..."
docker compose up -d daemon

echo "[DEPLOY] Готово. Логи: docker compose logs -f daemon"
