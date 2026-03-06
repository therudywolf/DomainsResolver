#!/usr/bin/env bash
# DMTCDRK — единая точка входа. Debian 12, только Docker.
# ./start.sh — подготовка + WireGuard + проверка + daemon

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
  echo "      Заполни GIT_PUSH_TOKEN в .env. Конфиг WG: wg/forestserver_DE-DE-578.conf"
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

# verify_input.txt (для первой проверки)
if [ ! -f verify_input.txt ]; then
  echo "      Создаю verify_input.txt для проверки..."
  { echo "# verify"; echo "example.com"; echo "github.com"; } > verify_input.txt
  echo ""
fi

# Сборка
echo "[3/4] Сборка образов..."
docker compose build -q

# WireGuard: проверка конфига и подъём туннеля
[ -f .env ] && set -a && . ./.env 2>/dev/null && set +a || true
WG_CONF="${WG_CONF:-forestserver_DE-DE-578.conf}"
WG_PATH=""
if [ -f "wg/${WG_CONF}" ]; then
  WG_PATH="wg/${WG_CONF}"
elif [ -f "wg/${WG_CONF%.conf}.conf" ]; then
  WG_PATH="wg/${WG_CONF%.conf}.conf"
  WG_CONF="${WG_CONF%.conf}.conf"
else
  echo "[ERROR] Конфиг WG не найден: wg/${WG_CONF} или wg/forestserver_DE-DE-578.conf"
  echo "        Положи конфиг в wg/ и при необходимости задай WG_CONF в .env."
  exit 1
fi
echo "Запуск WireGuard (${WG_PATH})..."
docker compose up -d wireguard
echo "Ожидание handshake (до 15 с)..."
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  if docker compose exec -T wireguard wg show 2>/dev/null | grep -q "latest handshake"; then
    echo "Туннель поднят."
    break
  fi
  [ "$i" -eq 15 ] && echo "[WARN] Handshake не получен за 15 с. Проверь: ./verify_wg.sh"
  sleep 1
done
echo ""

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

# Сразу пуш (пустой output если нет — чтобы видеть что push работает)
echo "Начальный push..."
[ -f .env ] && set -a && . <(sed 's/\r$//' .env) && set +a
OUTPUT_FILE="${OUTPUT_FILE:-output_optimized.txt}"
HASH_FILE="${HASH_FILE:-.input_hash}"
INPUT_FILE="${INPUT_FILE:-input.txt}"
if [ ! -f "$OUTPUT_FILE" ]; then
  touch "$OUTPUT_FILE"
fi
if [ ! -f "$HASH_FILE" ] && [ -f "$INPUT_FILE" ]; then
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$INPUT_FILE" | cut -d' ' -f1 > "$HASH_FILE"
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$INPUT_FILE" | cut -d' ' -f1 > "$HASH_FILE"
  else
    echo "init" > "$HASH_FILE"
  fi
fi
OUTPUT_FILE="$OUTPUT_FILE" HASH_FILE="$HASH_FILE" bash sync.sh

echo ""
echo "  Готово. Логи: docker compose logs -f daemon"
echo ""
