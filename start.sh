#!/usr/bin/env bash
# DMTCDRK — единая точка входа. Debian 12, только Docker.
# ./start.sh — подготовка + проверка + запуск daemon

set -e
cd "$(dirname "$0")"

echo ""
echo "  DMTCDRK"
echo "  ======="
echo ""

# Docker
if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] Docker не установлен."
  echo "  Debian 12: apt update && apt install -y docker.io docker-compose-v2"
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "[ERROR] docker compose не найден. Установите docker-compose-v2"
  exit 1
fi

# .env
if [ ! -f .env ]; then
  echo "[1/4] Создаю .env из .env.example..."
  cp .env.example .env
  echo "      Заполни GIT_PUSH_TOKEN и DNS_OVER_TLS_SERVERS в .env"
  echo ""
fi
[ -f .env ] && sed -i 's/\r$//' .env 2>/dev/null || true

# input.txt
if [ ! -f input.txt ]; then
  echo "[2/4] Создаю input.txt из input.txt.example..."
  cp input.txt.example input.txt
  echo "      Добавь домены в input.txt"
  echo ""
fi

# Сборка
echo "[3/4] Сборка образа..."
docker compose build -q

# Проверка (первый раз)
if [ ! -f .start_done ]; then
  echo "[4/4] Первый запуск — проверка DNS и push..."
  if docker compose --profile verify run --rm verify; then
    touch .start_done
  else
    echo ""
    echo "[WARN] Проверка не прошла. Заполни .env и повтори."
    exit 1
  fi
  echo ""
fi

# Daemon
echo "Запуск daemon..."
docker compose up -d daemon

echo ""
echo "  Готово. Логи: docker compose logs -f daemon"
echo ""
