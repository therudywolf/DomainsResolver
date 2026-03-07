#!/usr/bin/env bash
# DMTCDRK — единая точка входа. Debian 12, только Docker.
# ./start.sh — подготовка + проверка + запуск daemon

set -e
cd "$(dirname "$0")"

# Чтобы контейнер мог писать .input_hash и др., запускаем его от владельца каталога
if [ -z "$DOCKER_UID" ] || [ -z "$DOCKER_GID" ]; then
  if command -v stat >/dev/null 2>&1; then
    if stat -c '%u' . >/dev/null 2>&1; then
      export DOCKER_UID=$(stat -c '%u' .) DOCKER_GID=$(stat -c '%g' .)
    elif stat -f '%u' . >/dev/null 2>&1; then
      export DOCKER_UID=$(stat -f '%u' .) DOCKER_GID=$(stat -f '%g' .)
    fi
  fi
  DOCKER_UID="${DOCKER_UID:-1000}"
  DOCKER_GID="${DOCKER_GID:-1000}"
  export DOCKER_UID DOCKER_GID
fi

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
# Если скрипт запущен под root, отдать файлы владельцу каталога — иначе контейнер не сможет писать
if [ "$(id -u)" = "0" ] && [ -n "$DOCKER_UID" ] && [ -n "$DOCKER_GID" ] && command -v chown >/dev/null 2>&1; then
  for f in "$HASH_FILE" "$OUTPUT_FILE"; do
    [ -f "$f" ] && chown "${DOCKER_UID}:${DOCKER_GID}" "$f" 2>/dev/null || true
  done
fi
OUTPUT_FILE="$OUTPUT_FILE" HASH_FILE="$HASH_FILE" bash sync.sh

echo ""
echo "  Готово. Логи: docker compose logs -f daemon"
echo ""
